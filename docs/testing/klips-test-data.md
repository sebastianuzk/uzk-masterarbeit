# KLIPS Tool Test Data Sets

This document describes the test data sets for testing the KLIPS application tool without submitting actual applications.

## Overview

The KLIPS apply tool (`klips2_apply_study`) allows automated completion of study program applications. These test data sets have been designed to fill in all required information and navigate through the wizard up to (but not including) the final submission.

## Test Files

### 1. Simple Minimal Test
**File**: `src/dev/test_klips_apply_simple.py`

Minimal data set with only required fields:
- Study program: Rechtswissenschaften (Law)
- Semester: Wintersemester 2025/26
- Personal: Male, born in Köln
- Address: University address
- HZB: Allgemeine Hochschulreife (2.0)

**Use when**: Testing basic functionality with minimal input

### 2. Complete Test
**File**: `src/dev/test_klips_direct_complete.py`

Complete data set with all fields including optional ones:
- All fields from minimal test
- Additional nationality, birth country
- Complete address with country
- Detailed HZB information
- Support for previous studies (optional)

**Use when**: Testing full workflow with all possible fields

## Complete Test Data Set

Here's a verified working data set that reaches the end of the application process:

```python
{
    # Login Credentials
    "username": "tvaf7m1j",           # Test user
    "password": "zd92%!k3x98$oe",     # Test password
    
    # Study Program Selection
    "semester": "Wintersemester 2025/26",
    "degree_type": "Bachelor",
    "study_program": "Rechtswissenschaften",
    "entry_semester": "1",
    "study_form": "Erststudium",
    
    # Personal Data
    "birth_place": "Köln",
    "birth_country": "Deutschland",
    "nationality": "Deutschland",
    "gender": "Männlich",
    
    # Address Information
    "street": "Albertus-Magnus-Platz 1",
    "zip_code": "50923",
    "city": "Köln",
    "country": "Deutschland",
    "phone": "0221 470-0",
    
    # HZB (Hochschulzugangsberechtigung)
    "hzb_date": "15.06.2024",
    "hzb_type": "Allgemeine Hochschulreife",
    "hzb_grade": "2,0",
    "hzb_country": "Deutschland",
    "hzb_place": "Köln",
    
    # Previous Studies (Optional)
    "prev_uni": None,
    "prev_program": None,
    "prev_degree": None,
    "prev_semesters": None,
}
```

## Alternative Scenarios

### Scenario 1: BWL Bachelor (Female Applicant)
```python
{
    "study_program": "Betriebswirtschaftslehre",
    "semester": "Wintersemester 2025/26",
    "degree_type": "Bachelor",
    "entry_semester": "1",
    "study_form": "Erststudium",
    "birth_place": "Bonn",
    "gender": "Weiblich",
    "street": "Universitätsstraße 1",
    "zip_code": "50937",
    "city": "Köln",
    "phone": "0221 470-1234",
    "hzb_date": "20.07.2024",
    "hzb_type": "Allgemeine Hochschulreife",
    "hzb_grade": "1,5",
    "hzb_place": "Bonn",
}
```

### Scenario 2: Master with Previous Studies
```python
{
    "semester": "Sommersemester 2026",
    "degree_type": "Master",
    "study_program": "Wirtschaftsinformatik",
    "entry_semester": "1",
    "study_form": "Erststudium",
    "birth_place": "Düsseldorf",
    "gender": "Männlich",
    "street": "Meister-Ekkehart-Straße 11",
    "zip_code": "50937",
    "city": "Köln",
    "phone": "0221 470-5678",
    "hzb_date": "15.06.2020",
    "hzb_type": "Allgemeine Hochschulreife",
    "hzb_grade": "2,3",
    "hzb_place": "Düsseldorf",
    "prev_uni": "Universität zu Köln",
    "prev_program": "Informatik",
    "prev_degree": "Bachelor of Science",
    "prev_semesters": "6",
}
```

### Scenario 3: Zweitstudium (Second Degree)
```python
{
    "semester": "Wintersemester 2025/26",
    "degree_type": "Bachelor",
    "study_program": "Rechtswissenschaften",
    "entry_semester": "1",
    "study_form": "Zweitstudium",
    "birth_place": "Aachen",
    "gender": "Divers",
    "street": "Zülpicher Straße 77",
    "zip_code": "50937",
    "city": "Köln",
    "phone": "0221 470-9999",
    "hzb_date": "01.07.2018",
    "hzb_type": "Allgemeine Hochschulreife",
    "hzb_grade": "1,8",
    "hzb_place": "Aachen",
    "prev_uni": "RWTH Aachen",
    "prev_program": "Maschinenbau",
    "prev_degree": "Bachelor of Science",
    "prev_semesters": "7",
}
```

## Field Reference

### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `username` | string | KLIPS username | "tvaf7m1j" |
| `password` | string | KLIPS password | "zd92%!k3x98$oe" |
| `semester` | string | Application semester | "Wintersemester 2025/26" |
| `degree_type` | string | Type of degree | "Bachelor", "Master", "Promotionsstudium" |
| `study_program` | string | Name of program | "Rechtswissenschaften", "BWL" |
| `entry_semester` | string | Entry semester number | "1" |
| `study_form` | string | Type of study | "Erststudium", "Zweitstudium" |
| `birth_place` | string | City of birth | "Köln" |
| `gender` | string | Gender | "Männlich", "Weiblich", "Divers" |
| `street` | string | Street and number | "Albertus-Magnus-Platz 1" |
| `zip_code` | string | Postal code | "50923" |
| `city` | string | City name | "Köln" |
| `phone` | string | Phone number | "0221 470-0" |
| `hzb_date` | string | HZB date | "15.06.2024" (DD.MM.YYYY) |
| `hzb_type` | string | HZB type | "Allgemeine Hochschulreife" |
| `hzb_grade` | string | HZB grade | "2,0" |
| `hzb_place` | string | HZB location | "Köln" |

### Optional Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `birth_country` | string | Country of birth | "Deutschland" (default) |
| `nationality` | string | Nationality | "Deutschland" (default) |
| `country` | string | Address country | "Deutschland" (default) |
| `hzb_country` | string | HZB country | "Deutschland" (default) |
| `prev_uni` | string | Previous university | "Universität zu Köln" |
| `prev_program` | string | Previous program | "Informatik" |
| `prev_degree` | string | Previous degree | "Bachelor of Science" |
| `prev_semesters` | string | Number of semesters | "6" |

## Running Tests

### Prerequisites
1. Activate the virtual environment:
```bash
source .venv/bin/activate
```

2. Set environment variables in `.env`:
```bash
KLIPS_USERNAME=tvaf7m1j
KLIPS_PASSWORD=zd92%!k3x98$oe
KLIPS_HEADLESS=false  # Set to false to watch the browser
```

### Run Simple Test
```bash
source .venv/bin/activate && python3 src/dev/test_klips_apply_simple.py
```

### Run Complete Test
```bash
source .venv/bin/activate && python3 src/dev/test_klips_direct_complete.py
```

### Run with Agent
```bash
source .venv/bin/activate && python3 src/dev/test_klips_minimal.py
```

## Expected Behavior

1. **Browser Opens**: A Chromium browser window opens (when `KLIPS_HEADLESS=false`)
2. **Login**: Tool logs in with provided credentials
3. **Navigation**: Navigates to "Bewerbungen" section
4. **Form Filling**: Fills in all wizard steps:
   - Study program selection
   - Personal data
   - Address information
   - HZB information
   - Academic background (if applicable)
5. **Stops Before Submission**: Tool completes all forms but DOES NOT submit
6. **Success Message**: Returns success message with tabs visited

## Troubleshooting

### Login Fails
- Check credentials in `.env` file
- Verify KLIPS2 is accessible
- Check if test user account is still active

### Navigation Fails
- KLIPS2 interface may have changed
- Check browser console for JavaScript errors
- Verify selectors in `apply.py` are still valid

### Form Fields Not Filled
- Check if field names match KLIPS2 labels
- Some fields may be pre-filled for test user
- Verify data format matches KLIPS2 expectations

## Notes

- **DO NOT SUBMIT**: These tests are designed to stop before final submission
- **Test Account**: Use only designated test accounts
- **Data Format**: Follow German date format (DD.MM.YYYY) and grade format (comma as decimal separator)
- **Browser Visibility**: Set `KLIPS_HEADLESS=false` to watch automation for debugging
