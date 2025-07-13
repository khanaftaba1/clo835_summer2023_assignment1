from flask import Flask, render_template, request, send_file
from pymysql import connections
import os
import random
import argparse
import boto3
import requests
import logging
from botocore.exceptions import ClientError


app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DBHOST = os.environ.get("DBHOST") or "localhost"
DBUSER = os.environ.get("DBUSER") or "root"
DBPWD = os.environ.get("DBPWD") or "passwors"
DATABASE = os.environ.get("DATABASE") or "employees"
DBPORT = int(os.environ.get("DBPORT") or "3306")

# Application configuration
COLOR_FROM_ENV = os.environ.get('APP_COLOR') or "pink"
STUDENT_NAME = os.environ.get('STUDENT_NAME') or "Student"
BACKGROUND_IMAGE_URL = os.environ.get('BACKGROUND_IMAGE_URL') or ""

# S3 configuration
S3_BUCKET = os.environ.get('S3_BUCKET')
S3_IMAGE_KEY = os.environ.get('S3_IMAGE_KEY')
LOCAL_IMAGE_PATH = "/tmp/background_image.jpg"

# Create a connection to the MySQL database
db_conn = connections.Connection(
    host= DBHOST,
    port=DBPORT,
    user= DBUSER,
    password= DBPWD, 
    db= DATABASE
    
)
output = {}
table = 'employee';

# Define the supported color codes
color_codes = {
    "red": "#e74c3c",
    "green": "#16a085",
    "blue": "#89CFF0",
    "blue2": "#30336b",
    "pink": "#f4c2c2",
    "darkblue": "#130f40",
    "lime": "#C1FF9C",
}


# Create a string of supported colors
SUPPORTED_COLORS = ",".join(color_codes.keys())

# Generate a random color
COLOR = random.choice(["red", "green", "blue", "blue2", "darkblue", "pink", "lime"])

def download_background_image():
    """Download background image from S3 bucket"""
    try:
        if S3_BUCKET and S3_IMAGE_KEY:
            logger.info(f"Downloading background image from S3: s3://{S3_BUCKET}/{S3_IMAGE_KEY}")
            
            # Create S3 client
            s3_client = boto3.client('s3')
            
            # Download the image
            s3_client.download_file(S3_BUCKET, S3_IMAGE_KEY, LOCAL_IMAGE_PATH)
            logger.info(f"Background image downloaded successfully to {LOCAL_IMAGE_PATH}")
            return True
        elif BACKGROUND_IMAGE_URL:
            logger.info(f"Downloading background image from URL: {BACKGROUND_IMAGE_URL}")
            
            # Download from URL
            response = requests.get(BACKGROUND_IMAGE_URL)
            response.raise_for_status()
            
            with open(LOCAL_IMAGE_PATH, 'wb') as f:
                f.write(response.content)
            logger.info(f"Background image downloaded successfully to {LOCAL_IMAGE_PATH}")
            return True
        else:
            logger.warning("No background image URL or S3 configuration provided")
            return False
    except Exception as e:
        logger.error(f"Error downloading background image: {str(e)}")
        return False

def get_background_image_path():
    """Get the path to the background image"""
    if os.path.exists(LOCAL_IMAGE_PATH):
        return LOCAL_IMAGE_PATH
    return None

@app.route('/background-image')
def serve_background_image():
    """Serve the background image"""
    if os.path.exists(LOCAL_IMAGE_PATH):
        return send_file(LOCAL_IMAGE_PATH, mimetype='image/jpeg')
    else:
        return '', 404


@app.route("/", methods=['GET', 'POST'])
def home():
    background_image = get_background_image_path()
    return render_template('addemp.html', 
                         color=color_codes[COLOR], 
                         student_name=STUDENT_NAME,
                         background_image=background_image)

@app.route("/about", methods=['GET','POST'])
def about():
    background_image = get_background_image_path()
    return render_template('about.html', 
                         color=color_codes[COLOR], 
                         student_name=STUDENT_NAME,
                         background_image=background_image)
    
@app.route("/addemp", methods=['POST'])
def AddEmp():
    emp_id = request.form['emp_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    primary_skill = request.form['primary_skill']
    location = request.form['location']

  
    insert_sql = "INSERT INTO employee VALUES (%s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    try:
        
        cursor.execute(insert_sql,(emp_id, first_name, last_name, primary_skill, location))
        db_conn.commit()
        emp_name = "" + first_name + " " + last_name

    finally:
        cursor.close()

    print("all modification done...")
    background_image = get_background_image_path()
    return render_template('addempoutput.html', 
                         name=emp_name, 
                         color=color_codes[COLOR],
                         student_name=STUDENT_NAME,
                         background_image=background_image)

@app.route("/getemp", methods=['GET', 'POST'])
def GetEmp():
    background_image = get_background_image_path()
    return render_template("getemp.html", 
                         color=color_codes[COLOR],
                         student_name=STUDENT_NAME,
                         background_image=background_image)


@app.route("/fetchdata", methods=['GET','POST'])
def FetchData():
    emp_id = request.form['emp_id']

    output = {}
    select_sql = "SELECT emp_id, first_name, last_name, primary_skill, location from employee where emp_id=%s"
    cursor = db_conn.cursor()

    try:
        cursor.execute(select_sql,(emp_id))
        result = cursor.fetchone()
        
        # Add No Employee found form
        output["emp_id"] = result[0]
        output["first_name"] = result[1]
        output["last_name"] = result[2]
        output["primary_skills"] = result[3]
        output["location"] = result[4]
        
    except Exception as e:
        print(e)

    finally:
        cursor.close()

    background_image = get_background_image_path()
    return render_template("getempoutput.html", 
                         id=output["emp_id"], 
                         fname=output["first_name"],
                         lname=output["last_name"], 
                         interest=output["primary_skills"], 
                         location=output["location"], 
                         color=color_codes[COLOR],
                         student_name=STUDENT_NAME,
                         background_image=background_image)

if __name__ == '__main__':
    
    # Check for Command Line Parameters for color
    parser = argparse.ArgumentParser()
    parser.add_argument('--color', required=False)
    args = parser.parse_args()

    if args.color:
        print("Color from command line argument =" + args.color)
        COLOR = args.color
        if COLOR_FROM_ENV:
            print("A color was set through environment variable -" + COLOR_FROM_ENV + ". However, color from command line argument takes precendence.")
    elif COLOR_FROM_ENV:
        print("No Command line argument. Color from environment variable =" + COLOR_FROM_ENV)
        COLOR = COLOR_FROM_ENV
    else:
        print("No command line argument or environment variable. Picking a Random Color =" + COLOR)

    # Check if input color is a supported one
    if COLOR not in color_codes:
        print("Color not supported. Received '" + COLOR + "' expected one of " + SUPPORTED_COLORS)
        exit(1)

    # Download background image on startup
    logger.info("Starting application...")
    download_background_image()

    app.run(host='0.0.0.0', port=81, debug=True)
