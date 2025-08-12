# Grafana-Cortensor Setup

This folder contains the necessary files and instructions to set up Grafana, Loki and Mimir for monitoring and logging purposes. Please follow the steps below to configure and run the services.

## Prerequisites

- Ensure you have Docker and Docker Compose installed on your machine.

## Setup Instructions

### 1. Configure Nginx

Before proceeding, update the Nginx configuration with your domain name:

- Open `config/nginx.conf` in an editor.
- Replace all instances of `yourdomain.com` with your actual domain.

OR

```bash
sed -i 's/yourdomain.com/your-real-domain.com/g' config/nginx.conf
```

### 2. Prerequisites Tasks

To ensure proper permissions for Grafana and Loki, execute the following commands:

```bash
# Change permissions for Grafana
sudo chown -R 472:472 grafana-data/

# Change permissions for Loki
sudo chown -R 10001:10001 loki-data/
```

### 3. Start Services

Once the configuration and permissions are set, you can start the services using Docker Compose:

```bash
docker-compose up -d
```

This command will start LGM Stack in detached mode.

## Accessing Grafana

After starting the services, Grafana should be accessible at `http://your-real-domain.com` using the domain you configured.

* Default admin username and password is `admin/admin`.
* To disable the no login access, change the `GF_AUTH_ANONYMOUS_ENABLED` environment variable to `false` in the `grafana` service in the `docker-compose.yml` file.

## Enabling Auto SSL via Cloudflare with Flexible SSL/TLS Setup

To secure your Grafana-Cortensor setup using Cloudflare's Flexible SSL, follow the steps below:

### Step 1: Set Up Cloudflare Flexible SSL

1. **Sign Up/Log In to Cloudflare**: If you don't have an account, sign up at [Cloudflare](https://www.cloudflare.com/).

2. **Add Your Site**: Go to the Cloudflare dashboard and add your domain.

3. **Update DNS**: Change your domain's nameservers to the ones provided by Cloudflare.

4. **Configure SSL/TLS**:
   - Navigate to the SSL/TLS section in the Cloudflare dashboard.
   - Set the SSL/TLS encryption mode to **Flexible**.

### Step 2: Verify SSL/TLS Configuration

**Verify SSL**: Visit your site using `https://your-real-domain.com` to ensure SSL is active.

### Step 3: Enable Always Use HTTPS

- In the Cloudflare dashboard, go to the **SSL/TLS** > **Edge Certificates** tab and enable **Always Use HTTPS** to redirect all HTTP requests to HTTPS.

### Additional Tips

- **Automatic HTTPS Rewrites**: Enable this option in Cloudflare to avoid mixed content issues.
- **Caching**: Utilize Cloudflare's caching settings to improve load times and reduce server load.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
