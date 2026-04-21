# 📊 Student Performance Analysis System (SPAS)

A web-based application for analyzing student performance across three tests with automated analysis and visual reports.

## 🎯 Features

- **User Authentication**: Secure login system for staff members
- **File Upload**: Support for CSV and Excel (.xlsx) files
- **Data Validation**: Automatic validation of uploaded data
- **Performance Analysis**:
  - Individual test analysis (average, highest, lowest, pass percentage)
  - Cumulative analysis across all tests
  - Student ranking and categorization
  - Progress tracking (improvement/decline)
- **Visual Reports**:
  - Histograms for marks distribution
  - Bar charts for average marks per test
  - Line charts for student progress
  - Pie charts for pass/fail distribution
  - Top and bottom performers comparison
- **Interactive Dashboard**: Easy-to-use interface with tabbed results

## 🛠️ Technology Stack

- **Backend**: Python 3.x, Flask
- **Data Processing**: Pandas
- **Visualization**: Matplotlib, Seaborn
- **Frontend**: HTML, CSS, JavaScript

## 📋 Requirements

All dependencies are listed in `requirements.txt`:
- Flask==3.0.0
- pandas==2.1.4
- matplotlib==3.8.2
- seaborn==0.13.0
- openpyxl==3.1.2
- Werkzeug==3.0.1

## 🚀 Installation

1. **Clone or download this repository**

2. **Install dependencies** (if not already installed):
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python app.py
   ```

4. **Access the application**:
   Open your browser and navigate to: `http://localhost:5000`

## 🔐 Login Credentials

**Demo Accounts:**
- Username: `staff` | Password: `password123`
- Username: `admin` | Password: `admin123`

## 📂 File Format Requirements

Your CSV or Excel file must have the following structure:

| Name | Test1 | Test2 | Test3 |
|------|-------|-------|-------|
| Alice | 85 | 78 | 92 |
| Bob | 72 | 65 | 70 |
| Charlie | 45 | 55 | 60 |

**Rules:**
- Column names must match exactly: `Name`, `Test1`, `Test2`, `Test3`
- All marks must be numeric (0-100)
- No missing values allowed
- Supported formats: `.csv` or `.xlsx`

## 📊 Sample Data

A sample data file (`sample_data.csv`) is included with 20 students for testing purposes.

## 📁 Project Structure

```
SPAS/
├── app.py                  # Main Flask application
├── data_processor.py       # Data processing and analysis logic
├── requirements.txt        # Python dependencies
├── sample_data.csv        # Sample student data
├── templates/             # HTML templates
│   ├── base.html         # Base template
│   ├── login.html        # Login page
│   ├── dashboard.html    # Dashboard page
│   ├── upload.html       # File upload page
│   └── results.html      # Results display page
├── static/               # Static files
│   └── charts/          # Generated charts (auto-created)
└── uploads/             # Uploaded files (auto-created)
```

## 🎨 Features Overview

### 1. Dashboard
- Welcome screen with feature overview
- File format instructions
- Quick access to upload functionality

### 2. File Upload
- Drag-and-drop interface
- Real-time file validation
- Clear error messages

### 3. Analysis Results
- **Test Analysis Tab**: Individual test statistics
- **Student Tables Tab**: Top performers and students needing attention
- **Progress Tab**: Student improvement/decline tracking
- **Charts Tab**: Visual representations of all data

## 📈 Analysis Metrics

### Individual Test Analysis
- Average marks
- Highest marks
- Lowest marks
- Pass percentage (40% threshold)

### Cumulative Analysis
- Total students
- Overall average
- Pass/fail rates
- Student rankings
- Progress tracking (Test 1 → Test 3)

## 🔒 Security Features

- Password-based authentication
- Session management
- File type validation
- Secure file handling

## ⚠️ Limitations

- Basic authentication system (not production-ready)
- No database storage (session-based)
- Limited to 3 tests
- No real-time updates

## 🚀 Future Enhancements

- Multi-class comparison
- Subject-wise analysis
- PDF report download
- AI-based insights
- Database storage
- Advanced user management
- Email notifications

## 📝 Usage Instructions

1. **Login** with provided credentials
2. **Navigate** to Upload File page
3. **Select** your CSV or Excel file
4. **Wait** for validation and processing (2-5 seconds)
5. **View** comprehensive analysis and charts
6. **Switch** between tabs to explore different insights

## 🐛 Troubleshooting

**File Upload Fails:**
- Check column names match exactly
- Ensure all marks are numeric (0-100)
- Verify no empty cells exist

**Charts Not Displaying:**
- Ensure `static/charts/` directory exists
- Check file permissions
- Verify matplotlib is installed correctly

**Login Issues:**
- Use exact credentials provided
- Clear browser cache
- Check session handling

## 📞 Support

For issues or questions, please refer to the SRS document or contact the development team.

## 📄 License

This project is developed for academic institutions as per the Software Requirements Specification (SRS).

---

**Developed with ❤️ for Academic Excellence**
