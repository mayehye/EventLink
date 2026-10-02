Markdown

# EventLink 🎟️

![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Paystack](https://img.shields.io/badge/Paystack-091E42?style=for-the-badge&logo=paystack&logoColor=white)

EventLink is a comprehensive, Django-based event ticketing and management platform. It allows organizers to create, manage, and monetize events while providing attendees with a seamless ticket purchasing and QR-code-based check-in experience.

## 🚀 Features

### For Attendees

- **Event Discovery:** Browse events by category, search by keywords, and view curated "Happening Today" or "Promoted" events.
- **Tiered Ticketing:** Purchase standard admission or select from custom ticket tiers (e.g., VIP, VVIP, Tables).
- **Seamless Checkout:** Secure payments integrated natively via **Paystack**.
- **Ticket Management:** View purchased tickets in the "My Tickets" dashboard and download tickets with embedded, unique QR codes for entry.

### For Organizers

- **Comprehensive Dashboard:** Track gross revenue, platform fees, net share, and total tickets sold in real-time.
- **Flexible Event Creation:** Create free or paid events. Set up dynamic ticket tiers with custom capacities and pricing.
- **Smart Publication Fee System:** Configurable business model that automatically charges organizers a flat publication fee (via Paystack) to list free events, while taking a percentage commission from paid events.
- **QR Code Scanner:** Built-in web scanner to validate attendee tickets at the gate, preventing duplicate entries.
- **Attendee Management:** Export attendee lists as CSV files for external tracking.
- **Broadcast Announcements:** Send direct email announcements to all registered ticket holders for a specific event.

## 🛠️ Tech Stack

- **Backend:** Python 3, Django
- **Database:** PostgreSQL (Production via Supabase) / SQLite (Local Development)
- **Media Storage:** Cloudinary (For dynamic event poster hosting)
- **Payment Gateway:** Paystack API
- **QR Code Generation:** `qrcode` library
- **Frontend:** HTML5, CSS3, vanilla JavaScript, Bootstrap 5

## ⚙️ Local Development Setup

### Prerequisites

- Python 3.8+
- PostgreSQL installed locally (or a cloud instance like Supabase)
- A [Paystack](https://paystack.com/) account with test/live API keys
- A [Cloudinary](https://cloudinary.com/) account for media storage

### 1. Clone the Repository

```bash
git clone [https://github.com/yourusername/eventlink.git](https://github.com/yourusername/eventlink.git)
cd eventlink
2. Set Up a Virtual Environment
Bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
3. Install Dependencies
Bash
pip install -r requirements.txt
4. Environment Variables Configuration
Copy the example environment file to create your local active configuration:

Bash
cp .env.example .env
Open the .env file and populate it with your local development credentials:

Code snippet
# Django Security
SECRET_KEY=your_secure_django_secret_key
DEBUG=True # MUST be False in production!

# Database Configuration (PostgreSQL/Supabase)
DATABASE_URL=postgres://user:password@localhost:5432/eventlink_db

# Paystack API Keys
PAYSTACK_PUBLIC_KEY=pk_test_your_public_key
PAYSTACK_SECRET_KEY=sk_test_your_secret_key

# Cloudinary Storage
CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME

# Platform Business Logic
FREE_EVENT_PUBLISH_FEE=50.00
PAID_EVENT_COMMISSION=0.05

# Email Settings (For ticket receipts & broadcasts)
EMAIL_USER=eventlinkofficial@gmail.com
EMAIL_PASS=your_app_password
5. Apply Migrations
Bash
python manage.py makemigrations
python manage.py migrate
6. Create a Superuser (Admin)
Bash
python manage.py createsuperuser
7. Run the Development Server
Bash
python manage.py runserver
Visit http://127.0.0.1:8000 in your browser.

📦 Production Deployment Preparation
Before deploying to a hosting provider (e.g., Render, Railway, DigitalOcean):

Set DEBUG=False in your host's environment variables.

Provide the production DATABASE_URL (e.g., your Supabase connection string).

Provide live Paystack API keys.

Ensure django-cloudinary-storage is properly handling DEFAULT_FILE_STORAGE to prevent media loss on ephemeral filesystems.

🛡️️ Security Guidelines
API Keys: Live API keys, database passwords, and email app passwords must remain strictly out of the codebase.

Version Control: Ensure your .gitignore correctly filters out venv/, __pycache__/, media/, and .env before pushing to GitHub.

🤝 Contributing
Contributions, issues, and feature requests are welcome!

📝 License
This project is licensed under the MIT License.
```
