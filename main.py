from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status, Query
from pydantic import EmailStr
from models import UserRegistrationModel 
from models import BookReviewModel  
import cloudinary # type: ignore
import cloudinary.uploader # type: ignore
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.responses import HTMLResponse, JSONResponse
import bcrypt  # type: ignore
import os
from bson import ObjectId
import psutil # type: ignore
from welcomeEmail import send_email_via_gmail
from dotenv import load_dotenv
import redis.asyncio as redis  # type: ignore
import json

# Load environment variables from .env file
load_dotenv()

# Initialize Cloudinary with direct credentials
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# Initialize FastAPI
app = FastAPI(
    title="ReviewVerse API 📚",
    description="An API for book reviews, reader experiences, and ratings. Explore endpoints for submitting, updating, and retrieving reviews.",
    version="1.0.0",
    contact={
        "name": "ReviewVerse Support",
        "email": "reviewverseone@gmail.com",
    },
)

# Database setup (MongoDB with provided URI)
client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = client['reviewverse_db']

# MongoDB collections
users_collection = db["users"]
reviews_collection = db["reviews"]

# Get Redis connection details from environment variables
redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")
redis_password = os.getenv("REDIS_PASSWORD")
redis_ssl = os.getenv("REDIS_SSL") == "True"

# Redis connection setup
r = redis.Redis(
    host=redis_host,
    port=redis_port,
    password=redis_password,
    ssl=redis_ssl,
)



@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ReviewVerse API 📚</title>
             <link rel="icon" href="https://res.cloudinary.com/dpf5bkafv/image/upload/v1736681883/a8n3fwwqddw3jwexecy2.ico" type="image/x-icon">
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                margin: 0;
                padding: 0;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                height: 100vh;
                background-color: #f4f4f9;
            }
            h1 {
                color: #333;
                font-size: 3rem;
                margin-bottom: 20px;
            }
            p {
                color: #555;
                font-size: 1.2rem;
                margin: 10px 0;
            }
            a {
                text-decoration: none;
                color: #007bff;
                font-weight: bold;
                font-size: 1.1rem;
                margin-top: 15px;
                display: inline-block;
                transition: color 0.3s ease;
            }
            a:hover {
                color: #0056b3;
            }
            .cta-button {
                padding: 15px 30px;
                background-color: #28a745;
                color: white;
                font-size: 1.2rem;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                margin-top: 20px;
                transition: background-color 0.3s ease;
            }
            .cta-button:hover {
                background-color: #218838;
            }
            .footer {
                margin-top: 40px;
                font-size: 0.9rem;
                color: #777;
            }
        </style>
    </head>
    <body>
        <h1>Welcome to ReviewVerse API 📚</h1>
        <p>Your gateway to discovering and sharing book reviews, experiences, and ratings.</p>
        <p>Whether you're a bookworm or an occasional reader, our API offers a platform to share your reading journey.</p>
        <p>To get started with the API, visit our documentation page: <a href="/docs">/docs</a></p>
        <button class="cta-button" onclick="window.location.href='/docs'">Get Started</button>
        <div class="footer">
            <p>Built with ❤️ for book lovers everywhere.</p>
            <p>For questions or support, reach out to us at <a href="mailto:reviewverseone@gmail.com">reviewverseone@gmail.com</a></p>
        </div>
    </body>
    </html>
    """


# Endpoint to register a user
@app.post("/register")
async def register_user(
    username: str = Form(...),  # Making the username field required
    email: EmailStr = Form(...),  # Making the email field required
    password: str = Form(...),  # Making the password field required
    gender: str = Form(...),  # Making the gender field required
    age: int = Form(...),  # Making the age field required
    currentrole: str = Form(...),  # Making the currentrole field required
    profilephoto: UploadFile = File(...)  # Making the profilephoto field required
):
    # Validate role against predefined options
    valid_roles = ['student', 'employee', 'author', 'other']
    if currentrole not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid currentrole. Choose from 'student', 'employee', 'author', or 'other'"
        )
    
    # Validate gender against predefined options
    valid_genders = ['male', 'female', 'other']
    if gender not in valid_genders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid gender. Choose from 'male', 'female', or 'other'"
        )
    
    existing_user = await users_collection.find_one({"email": email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists"
        )
    
    try:
        # Upload profile photo to Cloudinary in 'reviewregister' folder
        upload_result = cloudinary.uploader.upload(profilephoto.file, folder="reviewregister")
        photo_url = upload_result['secure_url']
        
        # Hash the password before storing it
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Create a user object with the data (using UserRegistrationModel)
        user_data = UserRegistrationModel(
            username=username,
            email=email,
            password=hashed_password.decode('utf-8'),  # Convert bytes to string
            profilephoto=photo_url,
            gender=gender,
            age=age,
            currentrole=currentrole
        )

        # Convert the model to a dictionary and insert it into the users collection
        user_dict = user_data.dict()
        result = await users_collection.insert_one(user_dict)
        
        # Create a response object with the user data and inserted ID
        user_data_dict = {**user_dict, "_id": str(result.inserted_id)}

        send_email_via_gmail(receiver_email=email, receiver_name=username)

        return JSONResponse(content={"message": "User registered successfully", "user": user_data_dict})

    except Exception as e:
        # Handle potential errors, e.g., file upload failure, database insertion failure
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


# Endpoint to update user details by ID
@app.put("/update/{user_id}")
async def update_user(user_id: str, username: str = Form(...), gender: str = Form(...), age: int = Form(...), currentrole: str = Form(...)):
    # Validate role against predefined options
    valid_roles = ['student', 'employee', 'author', 'other']
    if currentrole not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid currentrole. Choose from 'student', 'employee', 'author', or 'other'"
        )
    
    # Validate gender against predefined options
    valid_genders = ['male', 'female', 'other']
    if gender not in valid_genders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid gender. Choose from 'male', 'female', or 'other'"
        )
    
    # Update the user in the database
    result = await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"username": username, "gender": gender, "age": age, "currentrole": currentrole}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return JSONResponse(content={"message": "User details updated successfully"})

# Endpoint to delete user by ID
@app.delete("/delete/{user_id}")
async def delete_user(user_id: str):
    result = await users_collection.delete_one({"_id": ObjectId(user_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return JSONResponse(content={"message": "User deleted successfully"})

# Endpoint to get all registered users' basic details
@app.get("/users")
async def get_users():
    """
    Fetch the list of users from MongoDB with Redis caching.
    """
    cache_key = "users_list"
    
    # Check if data exists in Redis
    try:
        cached_users = await r.get(cache_key)
        if cached_users:
            print(f"Cache hit for users: {cached_users}")
            users = json.loads(cached_users)
            return JSONResponse(content={"users": users})
    except Exception as e:
        print(f"Error fetching from Redis: {e}")
    
    # If not in cache, fetch from MongoDB
    try:
        users_cursor = users_collection.find({}, {"_id": 0, "username": 1, "gender": 1, "age": 1, "currentrole": 1})
        users = await users_cursor.to_list(length=None)
        print(f"Fetched users from MongoDB: {users}")
        
        # Cache the result in Redis with a TTL (e.g., 600 seconds = 10 minutes)
        await r.setex(cache_key, 600, json.dumps(users))  # Await Redis setex command
        print("Data saved in Redis successfully..")
        
        return JSONResponse(content={"users": users})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {e}")




# Helper function to convert ObjectId to string for response
def str_objectid(id: ObjectId) -> str:
    return str(id)

# Endpoint to get user details by ID
@app.get("/user/{id}")
async def get_user_by_id(id: str):
    # Convert the id from string to ObjectId
    try:
        user_id = ObjectId(id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format."
        )
    
    # Fetch the user from the database
    user = await users_collection.find_one({"_id": user_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    
    # Return user details (excluding the password for security reasons)
    user_details = {
        "username": user["username"],
        "email": user["email"],
        "gender": user["gender"],
        "age": user["age"],
        "currentrole": user["currentrole"],
        "profilephoto": user["profilephoto"]
    }

    return JSONResponse(content={"message": "User details retrieved successfully", "user": user_details})


# Endpoint to login a user
@app.post("/login")
async def login_user(
    email: EmailStr = Form(...),  # The email field is required
    password: str = Form(...)  # The password field is required
):
    # Check if the user exists in the database
    user = await users_collection.find_one({"email": email})
    
    if not user:
        # If the user doesn't exist, return an error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials. User not found."
        )
    
    # Compare the provided password with the stored hashed password
    stored_password = user["password"]
    if not bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
        # If the passwords do not match, return an error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials. Incorrect password."
        )
    
    # If the user exists and the password matches, return success
    return JSONResponse(
        content={"message": "User logged in successfully", "user": {
            "username": user["username"],
            "email": user["email"],
            "gender": user["gender"],
            "age": user["age"],
            "currentrole": user["currentrole"]
        }}
    )

# Add book review endpoint
@app.post("/add-review")
async def add_review(
    bookname: str = Form(...),  # Book name is required
    bookauthor: str = Form(...),  # Book author is required
    bookphoto: UploadFile = File(None),  # Book photo is optional
    experience: str = Form(...),  # Experience is required
    readingstatus: str = Form(...),  # Reading status is required
    rating: float = Form(...),  # Rating is required
    buyplace: str = Form(...),  # Buy place is required
    satisfied: bool = Form(...),  # Satisfaction status is required
    user_id: str = Form(...)  # User ID is required
):
    # Validate the reading status and buy place
    valid_reading_status = ['start', 'continue', 'finished']
    if readingstatus not in valid_reading_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reading status. Choose from 'start', 'continue', or 'finished'"
        )
    
    valid_buy_places = ['online', 'offline']
    if buyplace not in valid_buy_places:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid buy place. Choose from 'online' or 'offline'"
        )

    # Validate rating
    if rating < 0 or rating > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be between 0 and 5"
        )

    # Check if the user exists
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    try:
        # Optional: Upload the book photo to Cloudinary
        photo_url = None
        if bookphoto:
            upload_result = cloudinary.uploader.upload(bookphoto.file, folder="bookreviews")
            photo_url = upload_result['secure_url']

        # Create a book review object with the data (using BookReviewModel)
        review_data = BookReviewModel(
            bookname=bookname,
            bookauthor=bookauthor,
            bookphoto=photo_url,
            experience=experience,
            readingstatus=readingstatus,
            rating=rating,
            buyplace=buyplace,
            satisfied=satisfied,
            user_id=user_id
        )

        # Convert the model to a dictionary and insert it into the reviews collection
        review_dict = review_data.dict()
        result = await reviews_collection.insert_one(review_dict)

        # Return the inserted review data with the new ID
        review_dict["_id"] = str(result.inserted_id)

        return JSONResponse(content={"message": "Book review added successfully", "review": review_dict})

    except Exception as e:
        # Catch any exception and return it as a response to the user
        return HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@app.get("/get-review/{review_id}")
async def get_review(review_id: str):
    # Fetch the review by review_id from the database
    review = await reviews_collection.find_one({"_id": ObjectId(review_id)})
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    # Convert the ObjectId to string for the response
    review["_id"] = str(review["_id"])
    
    return JSONResponse(content={"message": "Review fetched successfully", "review": review})

@app.get("/get-reviews")
async def get_reviews(page: int = 1, limit: int = 10):
    """
    Fetch reviews from MongoDB with Redis caching.
    Reviews are cached for 12 hours (43200 seconds).
    """
    # Define cache key based on page and limit to store reviews
    cache_key = f"reviews_page_{page}_limit_{limit}"

    # Check if reviews are cached in Redis
    cached_reviews = await r.get(cache_key)  # This should be awaited in async context
    
    # Redis returns bytes, so we need to decode it into a string
    if cached_reviews:
        reviews = json.loads(cached_reviews.decode("utf-8"))
        return JSONResponse(content={"message": "Reviews fetched from cache", "reviews": reviews})

    # If not cached, fetch from MongoDB
    skip = (page - 1) * limit
    reviews_cursor = reviews_collection.find().skip(skip).limit(limit)
    reviews = await reviews_cursor.to_list(length=limit)

    if not reviews:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No reviews found"
        )

    # Convert ObjectId to string for each review
    for review in reviews:
        review["_id"] = str(review["_id"])

    # Cache the reviews in Redis with a TTL of 12 hours (43200 seconds)
    await r.setex(cache_key, 43200, json.dumps(reviews))  # Using async setex

    return JSONResponse(content={"message": "Reviews fetched successfully", "reviews": reviews})



@app.put("/update-review/{user_id}/{review_id}")
async def update_review(
    user_id: str,
    review_id: str,
    bookname: str = Form(None),  # Book name is optional for update
    bookauthor: str = Form(None),  # Book author is optional for update
    bookphoto: UploadFile = File(None),  # Book photo is optional
    experience: str = Form(None),  # Experience is optional for update
    readingstatus: str = Form(None),  # Reading status is optional for update
    rating: float = Form(None),  # Rating is optional for update
    buyplace: str = Form(None),  # Buy place is optional for update
    satisfied: bool = Form(None)  # Satisfaction status is optional for update
):
    # Check if the review exists
    review = await reviews_collection.find_one({"_id": ObjectId(review_id), "user_id": user_id})
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found or user does not have permission"
        )

    # Validate reading status
    if readingstatus and readingstatus not in ['start', 'continue', 'finished']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reading status. Choose from 'start', 'continue', or 'finished'"
        )

    # Validate buy place
    if buyplace and buyplace not in ['online', 'offline']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid buy place. Choose from 'online' or 'offline'"
        )

    # Validate rating
    if rating is not None and (rating < 0 or rating > 5):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be between 0 and 5"
        )

    try:
        # Optional: Upload the book photo to Cloudinary
        photo_url = review.get('bookphoto')  # Keep the existing photo if no new one is provided
        if bookphoto:
            upload_result = cloudinary.uploader.upload(bookphoto.file, folder="bookreviews")
            photo_url = upload_result['secure_url']

        # Update the review data
        update_data = {}
        if bookname:
            update_data['bookname'] = bookname
        if bookauthor:
            update_data['bookauthor'] = bookauthor
        if experience:
            update_data['experience'] = experience
        if readingstatus:
            update_data['readingstatus'] = readingstatus
        if rating is not None:
            update_data['rating'] = rating
        if buyplace:
            update_data['buyplace'] = buyplace
        if satisfied is not None:
            update_data['satisfied'] = satisfied
        if photo_url:
            update_data['bookphoto'] = photo_url

        # Update the review in the database
        result = await reviews_collection.update_one(
            {"_id": ObjectId(review_id), "user_id": user_id},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

        return JSONResponse(content={"message": "Review updated successfully"})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.delete("/delete-review/{user_id}/{review_id}")
async def delete_review(
    user_id: str,
    review_id: str
):
    # Check if the review exists
    review = await reviews_collection.find_one({"_id": ObjectId(review_id), "user_id": user_id})
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found or user does not have permission"
        )

    try:
        # Delete the review from the database
        result = await reviews_collection.delete_one({"_id": ObjectId(review_id), "user_id": user_id})

        if result.deleted_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

        return JSONResponse(content={"message": "Review deleted successfully"})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")



@app.get("/filter", response_model=dict)
async def filter_reviews(
    bookname: str = Query(None),
    bookauthor: str = Query(None),
    readingstatus: str = Query(None),
    rating: str = Query(None),
    buyplace: str = Query(None),
    satisfied: bool = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    try:
        filter_query = {}

        if bookname:
            filter_query["bookname"] = {"$regex": bookname, "$options": "i"}
        if bookauthor:
            filter_query["bookauthor"] = {"$regex": bookauthor, "$options": "i"}
        if readingstatus:
            if readingstatus not in ["start", "continue", "finished"]:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid reading status. Choose from 'start', 'continue', or 'finished'.",
                )
            filter_query["readingstatus"] = readingstatus
        if rating:
            if ">" in rating:
                filter_query["rating"] = {"$gt": float(rating[1:])}
            elif "<" in rating:
                filter_query["rating"] = {"$lt": float(rating[1:])}
            elif ">=" in rating:
                filter_query["rating"] = {"$gte": float(rating[2:])}
            elif "<=" in rating:
                filter_query["rating"] = {"$lte": float(rating[2:])}
            else:
                filter_query["rating"] = float(rating)
        if buyplace:
            if buyplace not in ["online", "offline"]:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid buy place. Choose from 'online' or 'offline'.",
                )
            filter_query["buyplace"] = buyplace
        if satisfied is not None:
            filter_query["satisfied"] = satisfied

        skip = (page - 1) * page_size
        reviews_cursor = reviews_collection.find(filter_query).skip(skip).limit(page_size)

        # Convert ObjectId to string for JSON serialization
        reviews = [
            {**review, "_id": str(review["_id"])} for review in await reviews_cursor.to_list(length=page_size)
        ]
        total_reviews = await reviews_collection.count_documents(filter_query)

        return {
            "message": "Filtered reviews fetched successfully.",
            "total": total_reviews,
            "page": page,
            "page_size": page_size,
            "reviews": reviews,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")



# System Health
@app.get("/health")
async def health_status():
    # Get CPU and Memory usage percentages
    cpu_usage = psutil.cpu_percent(interval=1)  # CPU usage in percentage
    memory_usage = psutil.virtual_memory().percent  # Memory usage in percentage
    
    # Determine the health status based on CPU usage
    if cpu_usage > 90 or memory_usage > 90:
        status = "High Risk"
    elif cpu_usage > 80 or memory_usage > 80:
        status = "High Usage"
    elif cpu_usage > 70 or memory_usage > 70:
        status = "Moderate"
    else:
        status = "Healthy"
    
    return {
        "cpu_usage": cpu_usage,
        "memory_usage": memory_usage,
        "status": status
    }








