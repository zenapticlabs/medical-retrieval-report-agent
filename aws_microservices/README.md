# SharePoint Medical Chronology Lambda Function

This AWS Lambda function creates medical chronology summaries from files in SharePoint using OpenAI and uploads them to S3.

## Features

- **SharePoint Integration**: Recursively scans SharePoint folders for medical files
- **File Processing**: Extracts text from PDF, DOCX, and TXT files
- **AI Analysis**: Uses OpenAI GPT-4 to create medical chronologies
- **Template-Based**: Uses Medical_Chronology_Template.docx for consistent formatting
- **S3 Storage**: Uploads completed chronologies to S3 bucket
- **Smart Filtering**: Excludes files with "_CHR Claim" substring

## Prerequisites

1. **AWS SAM CLI** installed
2. **Docker** installed (for local testing)
3. **Python 3.12+** installed
4. **OpenAI API Key** - Provided in configuration
5. **SharePoint Access** - Azure AD application with proper permissions

## Setup

### 1. Install SAM CLI

```bash
# Ubuntu/Debian
wget https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip
unzip aws-sam-cli-linux-x86_64.zip -d sam-installation
sudo ./sam-installation/install
```

### 2. Build the Application

```bash
cd aws_microservices
sam build
```

## Local Testing

### Test Chronology Creation

```bash
sam local invoke SharePointChronologyFunction \
  --event events/chronology_test.json \
  --env-vars env.json
```

### Test with API Gateway

```bash
sam local start-api --env-vars env.json
```

Then test with curl:

```bash
curl -X POST http://localhost:3000/create-chronology \
  -H "Content-Type: application/json" \
  -d '{
    "path": "Document Summary Project/00_Complete/Adkisson, Patricia/Adkisson, Patricia_Proof Pages",
    "max_depth": 3,
    "patient_name": "Adkisson_Patricia"
  }'
```

## API Usage

### Request Format

```json
{
  "path": "SharePoint/folder/path",
  "max_depth": 3,
  "patient_name": "Patient_Name"
}
```

### Response Format

```json
{
  "success": true,
  "message": "Chronology created successfully for 6 files",
  "download_url": "https://s3.amazonaws.com/medical-chronology/...",
  "s3_bucket": "medical-chronology",
  "s3_key": "Document Summary Project/.../Chronology_Adkisson_Patricia_20241223_151030.docx",
  "files_processed": 6,
  "chronology_data": {
    "meta_table": {
      "patient_name": "Adkisson, Patricia",
      "date_of_birth": "MM/DD/YYYY",
      "date_of_incident": "MM/DD/YYYY",
      "attorney": "Not stated",
      "case_number": "Not stated",
      "preparation_date": "12/23/2024"
    },
    "medical_history_summary": "...",
    "chronological_records": [...],
    "record_index": [...]
  }
}
```

## Environment Variables

The function requires these environment variables:

- `TENANT_ID`: Azure AD Tenant ID
- `CLIENT_ID`: Azure AD Application Client ID
- `CLIENT_SECRET`: Azure AD Application Client Secret
- `SITE_ID`: SharePoint Site ID
- `OPENAI_API_KEY`: OpenAI API Key for GPT-4
- `S3_BUCKET`: S3 bucket name (default: "medical-chronology")

### Setting Up Local Environment

1. Copy the sample environment file:

   ```bash
   cp env.json.sample env.json
   ```
2. Edit `env.json` with your actual values:

   ```json
   {
     "SharePointChronologyFunction": {
       "TENANT_ID": "your-actual-tenant-id",
       "CLIENT_ID": "your-actual-client-id",
       "CLIENT_SECRET": "your-actual-client-secret",
       "SITE_ID": "your-actual-site-id",
       "OPENAI_API_KEY": "your-actual-openai-key",
       "S3_BUCKET": "medical-chronology"
     }
   }
   ```

**Important**: Never commit `env.json` to version control as it contains sensitive information.

## File Processing

### Supported File Types

- **PDF**: Extracts text using PyPDF2
- **DOCX/DOC**: Extracts text using python-docx
- **TXT**: Plain text files

### Filtering Rules

- Files containing "_CHR Claim" in the filename are automatically excluded
- Processes up to 10 files per invocation to avoid OpenAI token limits
- Recursive scanning with configurable depth limit

## Medical Chronology Features

### AI Analysis

Uses OpenAI GPT-4 with specialized medical prompt to:

- Extract patient information and demographics
- Create chronological timeline of medical events
- Organize findings by body system
- Generate medical record index
- Maintain strict date ordering (MM/DD/YYYY format)

### Template Integration

- Uses Medical_Chronology_Template.docx as base
- Fills in structured sections automatically
- Maintains professional medical formatting
- Generates standardized output format

### Output Naming

Files are saved as: `Chronology_{PatientName}_{YYYYMMDD_HHMMSS}.docx`

## Deployment

### Deploy to AWS

```bash
sam deploy --guided
```

### Deploy with Parameters

```bash
sam deploy \
  --parameter-overrides \
    TenantId=your-tenant-id \
    ClientId=your-client-id \
    ClientSecret=your-client-secret \
    SiteId=your-site-id \
    OpenAIApiKey=your-openai-api-key \
    S3Bucket=medical-chronology
```

## AWS Resources Created

- **Lambda Function**: SharePointChronologyFunction
- **API Gateway**: /create-chronology endpoint
- **S3 Bucket**: medical-chronology (with encryption)
- **IAM Roles**: Automatic permissions for S3 and CloudWatch

## Limitations

- **File Limit**: Processes maximum 10 files per invocation
- **File Size**: Limited by Lambda memory (2048 MB)
- **Timeout**: 15-minute maximum execution time
- **Token Limits**: OpenAI API token restrictions apply

## Security

- **Encryption**: S3 bucket encrypted with AES256
- **Access Control**: Restricted bucket access
- **Secrets**: OpenAI API key and SharePoint credentials secured
- **PHI Compliance**: Maintains medical data confidentiality

## Troubleshooting

### Common Issues

1. **Authentication Error**: Verify Azure AD application permissions
2. **File Not Found**: Ensure SharePoint path exists and is accessible
3. **OpenAI Error**: Check API key validity and token limits
4. **S3 Upload Error**: Verify bucket permissions and AWS credentials

### Logging

Function logs detailed information to CloudWatch for debugging.

## Example Usage

Test with the Adkisson, Patricia case:

```bash
sam local invoke SharePointChronologyFunction \
  --event events/chronology_test.json \
  --env-vars env.json
```

This will process files from:
`Document Summary Project/00_Complete/Adkisson, Patricia/Adkisson, Patricia_Proof Pages`

And create a chronology document uploaded to S3.


 1630  cd aws_microservices && sam build --use-container
 1631  sam local invoke SharePointChronologyFunction --event events/test_mock_chronology.json --env-vars env.json --profile medical_local
 1632  python3 test_document_creation.py
 1633  sam deploy --profile medical_local
 1634  sam build --use-container
 1635  sam deploy --profile medical_local
 1636  sam build --use_container
 1637  sam build --use-container
 1638  sam deploy --profile medical_local
