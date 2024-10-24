TODO

## Terraform Commands

1. Initialize
```bash
## cd to terraform directory
terraform init
```

2. Generare SSH keys
```bash
ssh-keygen -t rsa -b 4096 -C "ibkr-gateway" -f ~/.ssh/id_rsa_ibkr_gateway
```

3. Create main.tfstate file
```bash
do_token="(digital ocean API token)"
ssh_key_admin_user="~/.ssh/id_rsa_ibkr_gateway.pub"
do_region="sgp1"
do_node_size="s-1vcpu-512mb-10gb"
```

4. Download ssh certs to local machine for your domain. Such as those found on porkbun.com
```bash
unzip domain.com-ssl-bundle
```

