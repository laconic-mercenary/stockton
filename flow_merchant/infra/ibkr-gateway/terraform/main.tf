terraform {
  required_version = ">= 1.1.0"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.19.0"
    }
  }
}

##
# vars
##

variable "do_environment" {
  description = "Target environment, such as production or staging"
  default     = "pro"
}

variable "do_node_size" {
  description = "Size of the node nodes"
  default     = "s-1vcpu-1gb"
}

variable "do_node_count" {
  description = "Number of nodes"
  default     = 1
}

variable "do_loadbalancer_size" {
  description = "Size of the loadbalancer nodes"
  default     = "lb-small"
}

variable "do_loadbalancer_count" {
  description = "Number of nodes in loadbalancer - not the same as droplets"
  default     = 1
}

variable "do_token" {
  description = "Digitalocean API token"
}

variable "do_domain" {
  description = "Your public domain"
  default = "revanchism.net"
}

variable "do_region" {
  default     = "ams3"
  description = "The Digitalocean region where the droplet will be created."
}

variable "ssh_key_admin_user" {
  default     = "~/.ssh/id_rsa_flow_merchant.pub"
  description = "SSH key of the node user. This user has ability to sudo."
}

variable "env_IBKR_API_PORT" {
  default = 8080
  description = "Port for accessing the IBKR API"
}

variable "env_IBKR_CLIENT_ID" {
  description = "The Account ID used to make trades that uses the IBKR API"
}

##
# digital ocean API token
##

provider "digitalocean" {
  token = var.do_token
}

##
# bootstrap scripts for the droplets
## 

data "template_file" "ibkr_gateway_env" {
  template = file("${path.module}/../etc/ibkr_gateway/.env.tpl")
  vars = {
    ibkr_api_port = var.env_IBKR_API_PORT
    ibkr_api_client_id = var.env_IBKR_CLIENT_ID
    ibkr_gateway_password = random_password.gateway_password.result
  }
}

data "template_file" "cloud_init_node" {
  template = file("cloud-config.tpl")
  vars = {
    ssh_pub_key = digitalocean_ssh_key.admin_user_key.public_key
    ibkr_gateway_env_file  = data.template_file.ibkr_gateway_env.rendered
    ibkr_gateway_service_file = file("${path.module}/../etc/systemd/system/ibkr_gateway.service")
    ibkr_gateway_main_py = file("${path.module}/../python/main.py")
    ibkr_gateway_requirements_txt = file("${path.module}/../python/requirements.txt")
    ibkr_gateway_config_py = file("${path.module}/../python/config.py")
    ibkr_gateway_server_py = file("${path.module}/../python/server.py")
  }
}

##
# resources
## 

resource "random_password" "gateway_password" {
  length           = 24
  special          = false
}

resource "digitalocean_ssh_key" "admin_user_key" {
  name       = "${var.do_environment}-${var.do_region}-admin-user-key"
  public_key = file(var.ssh_key_admin_user)
}

resource "digitalocean_floating_ip" "gateway_ip" {
  count       = var.do_node_count
  region      = var.do_region
  droplet_id  = digitalocean_droplet.node[count.index].id
}

## the droplets that will host node (8080) and node-provider (8081)
resource "digitalocean_droplet" "node" {
  region        = var.do_region
  image         = "ubuntu-22-04-x64"
  name          = "${var.do_environment}-${var.do_region}-gateway-node-${count.index + 1}"
  size          = "${var.do_node_size}"
  user_data     = data.template_file.cloud_init_node.rendered
  count         = var.do_node_count
  resize_disk   = false
  ssh_keys      = [ digitalocean_ssh_key.admin_user_key.id ]
}

## firewall for the node nodes
resource "digitalocean_firewall" "node_fw" {
  name          = "${var.do_environment}-${var.do_region}-gateway-node-fw"
  droplet_ids   = [for droplet in digitalocean_droplet.node : droplet.id]
  depends_on    = [ digitalocean_droplet.node, digitalocean_loadbalancer.public_node_nodes ]
  
  ## only loadbalancer can route through the proxy
  inbound_rule {
    protocol                    = "tcp"
    port_range                  = "80"
    source_load_balancer_uids   = [ digitalocean_loadbalancer.public_node_nodes.id ]
  }

  ## warning - open port 22 to all the of internet
  inbound_rule {
    protocol              = "tcp"
    port_range            = "22"
    source_addresses      = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "tcp"
    port_range            = "53-443"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "53"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

## a public layer4 loadbalancer for the node
resource "digitalocean_loadbalancer" "public_node_nodes" {
  name                    = "${var.do_environment}-${var.do_region}-gateway-node-lb"
  region                  = "${var.do_region}"
  size                    = "${var.do_loadbalancer_size}"
  size_unit               = var.do_loadbalancer_count
  algorithm               = "least_connections"
  depends_on              = [ digitalocean_droplet.node ]
  redirect_http_to_https  = true

  forwarding_rule {
    entry_port     = 443
    entry_protocol = "https"

    target_port     = 80
    target_protocol = "http"

    tls_passthrough = false
    
    ### SSL certificate_name = digitalocean_certificate.public_node_nodes.name
  }

  healthcheck {
    port     = 80
    protocol = "http"
    path     = "/healthz"
    check_interval_seconds = 20
    response_timeout_seconds = 5
    healthy_threshold = 2
    unhealthy_threshold = 2
  }

  droplet_ids = [for droplet in digitalocean_droplet.node : droplet.id]
}

### SSL
# resource "digitalocean_certificate" "public_node_nodes" {
#   name              = "${var.do_environment}-${var.do_region}-gateway-node-lb-cert"
#   private_key       = file("~/.gateway-ssl-certs/private.key.pem")
#   leaf_certificate  = file("~/.gateway-ssl-certs/domain.cert.pem")
#   certificate_chain = file("~/.gateway-ssl-certs/intermediate.cert.pem")
# }

##
# outputs
##
