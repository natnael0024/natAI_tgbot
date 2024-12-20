# Step 1: Use an official Python runtime as the base image
FROM python:3.10-slim

# Step 2: Set the working directory inside the container
WORKDIR /app

# Step 3: Copy the current directory contents into the container
COPY . /app/

# Step 4: Install the necessary dependencies
RUN pip install --upgrade pip
RUN pip install -r reqts.txt

# Step 5: Set environment variables (you could also use an .env file later)
ENV TELEGRAM_BOT_API_KEY=${TELEGRAM_BOT_API_KEY}
ENV DATABASE_URL=${DATABASE_URL}
ENV GEMINI_API_KEY=${GEMINI_API_KEY}
ENV SI=${SI}

# Step 6: Expose the port the bot will run on (optional, for communication purposes)
EXPOSE 5000

# Step 7: Command to run the bot
CMD ["python", "telegrambot.py"]
