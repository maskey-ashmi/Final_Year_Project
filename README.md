 SenseSkin: Face Acne Detection and Skincare Routine Recommendation 

SenseSkin is an AI-powered web application that detects facial acne from uploaded images and recommends a skincare routine based on the predicted acne severity. The system combines Deep Learning for acne detection and Machine Learning for severity classification and personalized skincare recommendations. 

 Features 

* Detects acne from facial images.
* Acne detection using YOLOv8 (Ultralytics). 
* Acne severity classification using a Random Forest algorithm implemented from scratch 
* Personalized skincare routine recommendations.
* Simple and responsive web interface.
* End-to-end prediction pipeline from image upload to recommendation.

Project Architecture 

 
User Uploads Image
        │
        ▼
Face Detection using Haar Cascade 
        │
        ▼
YOLOv8 Object Detection
        │
        ▼
Feature Extraction
        │
        ▼
Random Forest (Implemented from Scratch)
        │
        ▼
Severity Classification
        │
        ▼
Skincare Routine Recommendation
```

---

 Technologies Used

Deep Learning

* YOLOv8 (Ultralytics)

Machine Learning

* Random Forest (Implemented from Scratch)

 Backend

* Python
* Flask

Frontend

* HTML
* CSS
* JavaScript

Libraries

* OpenCV
* NumPy
* Pandas
* Pillow
* Ultralytics
* Scikit-learn (for preprocessing/evaluation if applicable)

---

Dataset

The acne detection model was trained using an annotated facial acne dataset compatible with the YOLO object detection format. 
YOLOv8 Acne Detection Dataset- Source : Roboflow Universe ( https://universe.roboflow.com/osman-kagan-kurnaz/skin-detection-uvj1f/dataset/8 )
 

The Random Forest model uses extracted features from the detection pipeline to classify acne severity and generate skincare recommendations. (Synthetic data created: 5000 samples) 



---

 Machine Learning Pipeline

Step 1: Acne Detection

YOLOv8 detects acne lesions from the uploaded facial image and returns bounding boxes around detected acne regions.

 Step 2: Feature Extraction

Detection results are processed to extract meaningful features, such as:

* Number of detected acne lesions

* Detection confidence


 Step 3: Severity Classification

A Random Forest classifier implemented completely from scratch predicts the acne severity level. 

Unlike using libraries such as `sklearn.RandomForestClassifier`, this implementation includes:

* Decision Tree construction
* Bootstrap sampling
* Random feature selection
* Majority voting
* Prediction aggregation

This implementation was developed for educational purposes to understand ensemble learning algorithms at a deeper level.

 Step 4: Recommendation 

Based on the predicted severity level, SenseSkin recommends an appropriate skincare routine.

License

This project was developed as a Final Year Project for academic purposes.
