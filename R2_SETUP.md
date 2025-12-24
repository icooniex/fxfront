# Cloudflare R2 Setup Guide

## 1. สร้าง R2 Bucket

1. เข้า Cloudflare Dashboard
2. ไปที่ **R2** → **Create bucket**
3. ตั้งชื่อ bucket เช่น `fxfront-media`
4. เลือก Region (แนะนำ APAC)

## 2. สร้าง API Token

1. ใน R2 Dashboard → **Manage R2 API Tokens**
2. คลิก **Create API Token**
3. เลือก Permissions:
   - **Object Read & Write**
   - เลือก Bucket ที่สร้างไว้
4. สร้าง Token แล้วเก็บ:
   - Access Key ID
   - Secret Access Key
   - Endpoint URL (จะมีหน้าตา: `https://xxxxx.r2.cloudflarestorage.com`)

## 3. ตั้งค่า Custom Domain (Optional แต่แนะนำ)

### วิธีที่ 1: ใช้ R2.dev subdomain (ฟรี)
1. ใน Bucket Settings → **Public Access**
2. เปิดใช้งาน **Allow Access**
3. จะได้ URL: `https://pub-xxxxx.r2.dev`

### วิธีที่ 2: ใช้ Custom Domain (แนะนำ)
1. ใน Bucket Settings → **Custom Domains**
2. คลิก **Connect Domain**
3. ใส่ subdomain เช่น `media.yourdomain.com`
4. Cloudflare จะสร้าง CNAME record อัตโนมัติ
5. รอ DNS propagate (1-5 นาที)

## 4. เพิ่ม Environment Variables ใน Railway

ไปที่ Railway Project → **Variables** เพิ่ม:

```bash
USE_R2_STORAGE=true
R2_ACCESS_KEY_ID=your_access_key_id
R2_SECRET_ACCESS_KEY=your_secret_access_key
R2_BUCKET_NAME=fxfront-media
R2_ENDPOINT_URL=https://xxxxx.r2.cloudflarestorage.com
R2_PUBLIC_DOMAIN=media.yourdomain.com  # ถ้าใช้ custom domain
```

**ถ้าไม่ใช้ custom domain:**
- เว้น `R2_PUBLIC_DOMAIN` ไว้ หรือไม่ต้องใส่
- URLs จะเป็น: `https://xxxxx.r2.cloudflarestorage.com/fxfront-media/payment_slips/...`

**ถ้าใช้ custom domain:**
- ใส่ `R2_PUBLIC_DOMAIN=media.yourdomain.com`
- URLs จะเป็น: `https://media.yourdomain.com/payment_slips/...`

## 5. Deploy

1. Commit และ push code
2. Railway จะ rebuild อัตโนมัติ
3. ทดสอบ upload payment slip หรือ backtest image
4. เช็คว่าไฟล์ขึ้นที่ R2 bucket

## 6. ทดสอบ

### ทดสอบใน Local (ไม่ใช้ R2)
```bash
# ไม่ต้องตั้งค่าอะไร ระบบจะใช้ local storage
python manage.py runserver
```

### ทดสอบใน Local (ใช้ R2)
```bash
# สร้าง .env file
echo "USE_R2_STORAGE=true" >> .env
echo "R2_ACCESS_KEY_ID=xxx" >> .env
echo "R2_SECRET_ACCESS_KEY=xxx" >> .env
echo "R2_BUCKET_NAME=fxfront-media" >> .env
echo "R2_ENDPOINT_URL=https://xxx.r2.cloudflarestorage.com" >> .env
echo "R2_PUBLIC_DOMAIN=media.yourdomain.com" >> .env  # optional

python manage.py runserver
```

## 7. Migration ไฟล์เก่า (ถ้ามี)

ถ้ามีไฟล์ใน `media/` อยู่แล้ว ให้ upload ขึ้น R2:

### วิธีที่ 1: ใช้ Cloudflare Dashboard
1. เข้า R2 Bucket
2. คลิก **Upload**
3. เลือกไฟล์ทั้งหมดจาก `media/payment_slips/` และ `media/backtest_curves/`
4. อัพโหลด (รักษา folder structure)

### วิธีที่ 2: ใช้ rclone (สำหรับไฟล์เยอะ)
```bash
# ติดตั้ง rclone
brew install rclone  # macOS

# ตั้งค่า rclone
rclone config

# Sync ไฟล์
rclone sync media/ r2:fxfront-media/ --progress
```

## 8. ราคา Cloudflare R2

- **Storage:** $0.015/GB/month
- **Egress (Download):** ฟรี! (ไม่จำกัด)
- **Operation:** 
  - Class A (Write): $4.50 per million requests
  - Class B (Read): $0.36 per million requests

**ตัวอย่างการใช้งาน:**
- 1,000 payment slips (50 KB each) = 50 MB
- 100 backtest images (500 KB each) = 50 MB
- รวม 100 MB = **$0.0015/month** (ประมาณ 0.05 บาท/เดือน)

## 9. Troubleshooting

### ไฟล์ไม่ขึ้น R2
- เช็ค Environment Variables ใน Railway
- เช็ค API Token Permissions
- เช็ค logs: `railway logs`

### URL ไม่ถูกต้อง
- เช็คว่าตั้ง `R2_PUBLIC_DOMAIN` ถูกต้องหรือไม่
- ถ้าไม่ใช้ custom domain ให้เอา variable นี้ออก

### 403 Forbidden
- เช็คว่า Bucket เปิด Public Access แล้ว
- เช็ค CORS settings ใน R2 bucket

## 10. CORS Settings (ถ้าต้องการ)

ถ้าต้องการให้ frontend อื่นดึงรูปได้ ให้ตั้ง CORS:

1. ไปที่ R2 Bucket → **Settings** → **CORS Policy**
2. เพิ่ม:

```json
[
  {
    "AllowedOrigins": ["https://yourdomain.com", "https://www.yourdomain.com"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["*"],
    "MaxAgeSeconds": 3600
  }
]
```

## สรุป

✅ ไฟล์เก็บถาวรบน R2 (ไม่หายเวลา deploy)  
✅ ราคาถูกมาก (เกือบฟรี)  
✅ Egress ฟรีไม่จำกัด  
✅ รองรับ custom domain  
✅ ใช้งานง่ายเหมือน S3
