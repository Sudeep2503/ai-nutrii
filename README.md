# NutriSense AI

NutriSense AI is a full-stack Flask application for nutritional deficiency detection and personalized nutrition guidance. The project is designed as a professional portfolio application with a clean architecture, modular routing, and a responsive healthcare-themed interface.

## Project Overview

This foundation includes:
- A polished landing page for the product
- Modular Flask blueprints for authentication, dashboard, prediction, admin, and AI planning
- Configuration support for MySQL and session management
- Template-based pages for future feature expansion

## Folder Structure

- app.py: Flask application entry point
- config.py: Application configuration
- routes/: Blueprint modules
- templates/: HTML templates
- static/: CSS, JavaScript, and images
- utils/: Shared utilities, including the database helper
- sql/: SQL scripts for database setup
- datasets/: Data files for future modeling work
- uploads/: File upload storage

## Technology Stack

- Frontend: HTML5, CSS3, Vanilla JavaScript
- Backend: Python, Flask
- Database: MySQL
- Future ML/AI: scikit-learn, pandas, NumPy, joblib, Google Gemini API

## Installation Steps

1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a MySQL database named `nutrisense` if you want to connect to the database layer.
5. Set environment variables if needed:
   ```bash
   set SECRET_KEY=your-secret-key
   set MYSQL_HOST=localhost
   set MYSQL_USER=root
   set MYSQL_PASSWORD=your-password
   set MYSQL_DATABASE=nutrisense
   set GEMINI_API_KEY=your-gemini-api-key
   ```

   If you do not set GEMINI_API_KEY, the app will still run and provide built-in nutrition guidance for the prediction results.

## How to Run

Start the Flask application:

```bash
python app.py
```

Open your browser at:

```text
http://127.0.0.1:5000/
```

## Dataset Description

The machine learning pipeline uses a realistic synthetic dataset stored in [datasets/nutritional_deficiencies.csv](datasets/nutritional_deficiencies.csv). It includes user lifestyle, dietary, symptom, and demographic features designed to support multi-class prediction of common nutritional deficiencies.

## Feature List

The model uses features such as age, gender, height, weight, BMI, activity level, sleep hours, water intake, sunlight exposure, diet type, meal frequency, fruit intake, vegetable intake, dairy intake, protein intake, fast food frequency, sugary drink consumption, smoking, alcohol, fatigue, weakness, hair loss, pale skin, muscle cramps, bone pain, frequent illness, headaches, poor concentration, and tingling sensation.

## Training Steps

1. Generate or update the dataset:
   ```bash
   python datasets/generate_dataset.py
   ```
2. Train the model:
   ```bash
   python models/train_model.py
   ```
3. The following artifacts are created:
   - models/nutrition_model.pkl
   - models/label_encoder.pkl
   - models/feature_columns.pkl
   - static/images/confusion_matrix.png
   - static/images/feature_importance.png
   - static/images/class_distribution.png

## Evaluation Metrics

The training script reports:
- Accuracy
- Precision
- Recall
- F1 Score
- Confusion Matrix
- Classification Report

## How to Retrain

Re-run the training command after changing the dataset or feature engineering logic:

```bash
python models/train_model.py
```

## Future Features

- User authentication and profile management
- Nutrition assessment workflows
- Predictive deficiency screening
- AI-generated dietary recommendations
- Secure admin dashboard and analytics
