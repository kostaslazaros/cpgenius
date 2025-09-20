# Prognosis Analysis API

This API provides functionality for analyzing large CSV files with prognosis data and running machine learning algorithms on selected prognosis values.

## Features

- **CSV File Upload**: Upload large CSV files containing a 'Prognosis' column
- **Prognosis Analysis**: Extract unique prognosis values and basic statistics
- **Machine Learning Algorithms**: Run various ML algorithms on selected prognosis values
- **Result Download**: Download processed results as CSV files
- **File Management**: List, view, and delete uploaded files and results

## API Endpoints

### 1. Upload CSV File
```
POST /prognosis/upload
```
Upload a CSV file with a 'Prognosis' column for analysis.

**Parameters:**
- `file`: CSV file (multipart/form-data)

**Response:**
```json
{
  "task_id": "uuid",
  "sha1_hash": "file_hash",
  "message": "CSV file uploaded successfully. Analysis started.",
  "filename": "file.csv",
  "file_size": 123456
}
```

### 2. Get Prognosis Values
```
GET /prognosis/prognosis-values/{sha1_hash}
```
Get unique values from the Prognosis column of an uploaded file.

**Response:**
```json
{
  "sha1_hash": "file_hash",
  "filename": "file.csv",
  "unique_values": ["High Risk", "Low Risk", "Normal"],
  "total_rows": 1000,
  "prognosis_column_found": true,
  "message": "Found 3 unique prognosis values"
}
```

### 3. Run Algorithm
```
POST /prognosis/run-algorithm
```
Run a machine learning algorithm on selected prognosis values.

**Request Body:**
```json
{
  "sha1_hash": "file_hash",
  "selected_prognosis_values": ["High Risk", "Low Risk"],
  "algorithm": "random_forest"
}
```

**Available Algorithms:**
- `logistic_regression`
- `random_forest`
- `svm`
- `neural_network`
- `gradient_boosting`

**Response:**
```json
{
  "task_id": "uuid",
  "sha1_hash": "file_hash",
  "algorithm": "random_forest",
  "selected_values": ["High Risk", "Low Risk"],
  "message": "Algorithm random_forest started for 2 prognosis values"
}
```

### 4. Check Task Status
```
GET /prognosis/status/{task_id}
```
Get the status of a running task.

**Response:**
```json
{
  "task_id": "uuid",
  "status": "SUCCESS",
  "result": {
    "sha1_hash": "file_hash",
    "algorithm": "random_forest",
    "accuracy": 0.95,
    "output_filename": "random_forest_High Risk_Low Risk_results.csv"
  }
}
```

### 5. List Results
```
GET /prognosis/results/{sha1_hash}
```
List all algorithm result files for a given file.

**Response:**
```json
{
  "sha1_hash": "file_hash",
  "result_count": 1,
  "results": [
    {
      "filename": "random_forest_High Risk_Low Risk_results.csv",
      "file_size": 45000,
      "created_time": 1234567890,
      "download_url": "/prognosis/download/file_hash/filename.csv"
    }
  ]
}
```

### 6. Download Result File
```
GET /prognosis/download/{sha1_hash}/{filename}
```
Download a result CSV file.

### 7. List All Files
```
GET /prognosis/list
```
List all uploaded CSV files.

### 8. Remove File
```
DELETE /prognosis/remove/{sha1_hash}
```
Remove a file and all its results.

### 9. Remove All Files
```
DELETE /prognosis/remove_all?delete_pass=123
```
Remove all files (requires password).

## CSV File Requirements

Your CSV file **MUST**:
1. **Have a column named exactly `Prognosis`** - This is mandatory and non-negotiable
2. **The Prognosis column must contain at least one non-null value** - Empty/null-only columns are rejected
3. **Contain numeric columns for machine learning features** - At least one numeric column besides Prognosis
4. **Be properly formatted CSV with headers** - Standard CSV format with comma separation

**⚠️ IMPORTANT**: Files without a valid Prognosis column will be **immediately rejected** during upload with a clear error message.

Example CSV structure:
```csv
Age,BMI,BloodPressure,Cholesterol,Glucose,HeartRate,Prognosis
45,25.2,120,200,95,70,Normal
60,30.1,140,250,110,75,High Risk
35,22.5,110,180,90,65,Low Risk
```

## Machine Learning Process

1. **Data Filtering**: Only rows with selected prognosis values are used
2. **Feature Selection**: All numeric columns (except Prognosis) are used as features
3. **Data Preprocessing**: Missing values filled with column means, features scaled
4. **Model Training**: 80% of data used for training, 20% for testing
5. **Evaluation**: Accuracy and classification report generated
6. **Prediction**: Full dataset predictions with confidence scores

## Output Files

For each algorithm run, the following files are generated:

1. **Results CSV**: `{algorithm}_{selected_values}_results.csv`
   - Original data + predictions + confidence scores
   - Sorted by prognosis values and confidence

2. **Trained Model**: `{algorithm}_{selected_values}_model.joblib`
   - Serialized scikit-learn model

3. **Scaler**: `{algorithm}_{selected_values}_scaler.joblib`
   - Feature scaler for consistent preprocessing

4. **Metadata**: `{algorithm}_{selected_values}_metadata.json`
   - Training statistics, accuracy, feature importance, etc.

## Testing

Use the provided test script to test the functionality:

```bash
uv run python test_prognosis_analysis.py
```

This will:
1. Create a sample CSV file with synthetic health data
2. Upload the file
3. Extract prognosis values
4. Run a Random Forest algorithm
5. Display results and accuracy

## Example Workflow

1. **Upload CSV**: Use the upload endpoint to upload your CSV file
2. **Get Task Status**: Monitor the analysis task until complete
3. **Get Prognosis Values**: Retrieve the unique prognosis values
4. **Select Values & Algorithm**: Choose which prognosis values to analyze and which algorithm to use
5. **Run Algorithm**: Start the machine learning task
6. **Monitor Progress**: Check task status until completion
7. **Download Results**: Get the processed CSV with predictions

## Error Handling

The API provides detailed error messages for common issues:
- Missing Prognosis column
- Invalid CSV format
- Empty datasets
- No numeric features
- Invalid algorithm selection

All errors include helpful messages to guide you in resolving the issue.