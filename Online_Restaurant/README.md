# AI-Enabled Online Restaurant Order and Delivery System

A comprehensive web application for restaurant order management with AI-powered customer service, built with Flask and designed for PythonAnywhere deployment.

## Features

- **User Management**: Registration, login, and role-based access (Customers, VIPs, Chefs, Delivery Personnel, Managers)
- **Menu Browsing**: Public menu with search and category filtering
- **Personalized Menu**: For logged-in users (most ordered, highest rated items)
- **Online Ordering**: Shopping cart and order placement system
- **Delivery Management**: Order bidding and assignment system
- **Chef Rating System**: Rate chefs after order delivery
- **Reputation Management**: File complaints/compliments with manager review
- **VIP Status**: Automatic promotion based on spending ($100+) or 3 orders without complaints
- **Warning System**: Automatic warnings for rejected complaints, blacklist after 3 warnings
- **AI Customer Service**: Local knowledge base with Hugging Face LLM fallback
- **HR Management**: Manager dashboard for employee management, salary adjustments
- **Finance Management**: Account deposits and balance tracking

## Installation

### Local Development

1. **Clone or navigate to the project directory:**
   ```bash
   cd restaurant_system
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Create a `.env` file (optional for local development):
   ```
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=sqlite:///restaurant.db
   HUGGINGFACE_API_KEY=your-huggingface-api-key-optional
   ```

5. **Initialize the database:**
   ```bash
   python app.py
   ```
   The database will be created automatically on first run.

6. **Run the application:**
   ```bash
   python app.py
   ```
   Access the application at `http://localhost:5000`

### Default Manager Account

- **Username:** `manager`
- **Password:** `manager123`
- **Change this password immediately in production!**

## PythonAnywhere Deployment

### 1. Upload Files

Upload all files to your PythonAnywhere account using the Files tab.

### 2. Configure Web App

1. Go to the **Web** tab in PythonAnywhere
2. Click **Add a new web app**
3. Choose **Flask** and Python 3.x
4. In the WSGI configuration file, replace the contents with:
   ```python
   import sys
   path = '/home/yourusername/restaurant_system'
   if path not in sys.path:
       sys.path.append(path)
   
   from wsgi import application
   ```

### 3. Configure Database (MySQL)

1. Go to the **Databases** tab
2. Create a new MySQL database (or use existing)
3. Update `config.py` with your MySQL connection string:
   ```python
   SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://username:password@hostname/database_name'
   ```
   Or set as environment variable in the Web tab:
   ```
   DATABASE_URL=mysql+pymysql://username:password@hostname/database_name
   ```

### 4. Set Environment Variables

In the **Web** tab, go to **Environment variables** and add:
- `SECRET_KEY`: A strong secret key for Flask sessions
- `DATABASE_URL`: MySQL connection string (if not in config.py)
- `HUGGINGFACE_API_KEY`: Your Hugging Face API key (optional)

### 5. Install Packages

In a **Bash console**, navigate to your project and install dependencies:
```bash
cd ~/restaurant_system
pip3.10 install --user -r requirements.txt
```

### 6. Initialize Database

Run once to create tables:
```bash
python3.10 -c "from app import app; from models import db; app.app_context().push(); db.create_all()"
```

### 7. Reload Web App

Click **Reload** in the Web tab to start the application.

## Configuration

### Database

- **Development**: Uses SQLite (`restaurant.db`)
- **Production**: Configure MySQL in `config.py` or via `DATABASE_URL` environment variable

### AI Service

The AI customer service uses:
1. **Local Knowledge Base**: `knowledge_base/restaurant_info.txt`
2. **Hugging Face API**: Falls back to Hugging Face Inference API if no local match

To configure Hugging Face:
1. Get an API key from [Hugging Face](https://huggingface.co/inference-api)
2. Set `HUGGINGFACE_API_KEY` environment variable
3. Optionally change the model in `config.py`

Default model: `google/flan-t5-base`

### File Uploads

Menu images should be placed in `static/images/`. Ensure the directory exists and has proper permissions.

## Project Structure

```
restaurant_system/
├── app.py                 # Main Flask application
├── config.py             # Configuration
├── models.py             # Database models
├── utils.py              # Helper functions
├── ai_service.py         # AI customer service
├── wsgi.py               # WSGI entry point for PythonAnywhere
├── requirements.txt      # Python dependencies
├── README.md             # This file
├── static/
│   ├── css/             # Stylesheets
│   ├── js/              # JavaScript files
│   └── images/          # Menu images
├── templates/            # HTML templates
└── knowledge_base/       # Local knowledge base
```

## Usage

### For Customers

1. Register for an account
2. Deposit money to your account
3. Browse the menu and add items to cart
4. Place orders
5. Rate chefs after delivery
6. File complaints/compliments as needed

### For Chefs

1. Login to chef dashboard
2. View orders with your items
3. Update order status (Preparing → Ready)

### For Delivery Personnel

1. Login and view available orders
2. Place bids on orders you want to deliver
3. Manager will assign orders
4. Update delivery status

### For Managers

1. Review pending complaints/compliments
2. Assign orders to delivery personnel based on bids
3. Manage employees (hire/fire, adjust salaries)
4. Review flagged knowledge base entries
5. Manage blacklist

## Requirements

- Python 3.8+
- Flask 3.0.0
- SQLAlchemy 2.0.23
- Other dependencies listed in `requirements.txt`

## Notes

- The system automatically promotes users to VIP status when criteria are met
- Complaints rejected by manager result in warnings
- 3 warnings = blacklist (all users)
- 2 warnings = demotion (VIP users)
- AI responses with 0-star ratings are automatically flagged for review

## License

This project is created for educational purposes.


