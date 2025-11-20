# คู่มือการ Deploy ไปยัง Railway

## ขั้นตอนการ Deploy

### 1. เตรียม Project
Project นี้พร้อม deploy แล้ว มีไฟล์ที่จำเป็นดังนี้:
- ✅ `requirements.txt` - Python dependencies
- ✅ `Procfile` - คำสั่งสำหรับรัน web server
- ✅ `runtime.txt` - เวอร์ชัน Python
- ✅ `railway.json` - การตั้งค่า Railway
- ✅ `build.sh` - สคริปต์สำหรับ build
- ✅ `.env.example` - ตัวอย่างการตั้งค่า environment variables

### 2. เริ่มต้นใช้งาน Railway

1. ไปที่ [Railway.app](https://railway.app) และสมัครสมาชิก/เข้าสู่ระบบ
2. คลิก "New Project"
3. เลือก "Deploy from GitHub repo"
4. เลือก repository ของคุณ

### 3. ตั้งค่า Environment Variables

ใน Railway Dashboard ให้เพิ่ม Environment Variables ดังนี้:

```bash
SECRET_KEY=your-secret-key-here-generate-a-new-one
DEBUG=False
ALLOWED_HOSTS=.railway.app
```

**สำคัญ:** สร้าง SECRET_KEY ใหม่โดยใช้คำสั่ง:
```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 4. เพิ่ม PostgreSQL Database (แนะนำ)

1. ใน Railway Project คลิก "+ New"
2. เลือก "Database" → "PostgreSQL"
3. Railway จะสร้าง `DATABASE_URL` environment variable อัตโนมัติ

**หมายเหตุ:** ถ้าไม่ใช้ PostgreSQL ระบบจะใช้ SQLite (ไม่แนะนำสำหรับ production)

### 5. Deploy

1. Railway จะ deploy อัตโนมัติเมื่อคุณ push code ไปยัง GitHub
2. รอให้ build เสร็จ (ดูได้จาก Deployments tab)
3. เมื่อเสร็จแล้วจะได้ URL สำหรับเข้าถึงเว็บไซต์

### 6. ตั้งค่า Domain (Optional)

1. ใน Railway Dashboard → Settings → Domains
2. คลิก "Generate Domain" หรือเพิ่ม custom domain ของคุณ
3. อัพเดท `ALLOWED_HOSTS` ใน Environment Variables:
   ```
   ALLOWED_HOSTS=.railway.app,yourdomain.com
   ```

## การอัพเดทโค้ด

เพียงแค่ push code ใหม่ไปยัง GitHub:
```bash
git add .
git commit -m "Update code"
git push
```

Railway จะ deploy อัตโนมัติ

## การตรวจสอบ Logs

1. ไปที่ Railway Dashboard
2. เลือก Deployment ที่ต้องการดู
3. คลิก "View Logs" เพื่อดู deployment และ runtime logs

## Static Files

Static files จะถูกจัดการโดย WhiteNoise อัตโนมัติ ไม่ต้องตั้งค่าเพิ่มเติม

## Media Files

สำหรับ media files (ไฟล์ที่ user อัพโหลด) แนะนำให้ใช้:
- AWS S3
- Cloudinary
- หรือ cloud storage service อื่นๆ

Railway ไม่เหมาะสำหรับเก็บ media files ถาวร เพราะ filesystem จะ reset ทุกครั้งที่ deploy ใหม่

## Troubleshooting

### Build Failed
- ตรวจสอบ logs ว่า dependencies ทั้งหมดติดตั้งได้หรือไม่
- ตรวจสอบ Python version ใน `runtime.txt`

### Internal Server Error
- ตรวจสอบ `SECRET_KEY` และ environment variables อื่นๆ
- ตรวจสอบ application logs

### Static Files ไม่โหลด
- รันคำสั่ง `python manage.py collectstatic` (ทำอัตโนมัติใน `build.sh` แล้ว)
- ตรวจสอบ `STATIC_ROOT` และ `STATIC_URL` ใน settings

## คำสั่งที่มีประโยชน์

### รัน migrations ใหม่
ใน Railway Dashboard → Settings → Service:
```bash
python manage.py migrate
```

### สร้าง superuser
```bash
python manage.py createsuperuser
```

### เข้าถึง Django shell
```bash
python manage.py shell
```

## Security Checklist

- ✅ `DEBUG = False` ใน production
- ✅ ใช้ `SECRET_KEY` ที่ปลอดภัยและไม่เปิดเผย
- ✅ ตั้งค่า `ALLOWED_HOSTS` ให้ถูกต้อง
- ✅ ใช้ HTTPS (Railway รองรับอัตโนมัติ)
- ✅ ใช้ PostgreSQL แทน SQLite
- ✅ อย่า commit `.env` file ลง git

## ทรัพยากรเพิ่มเติม

- [Railway Documentation](https://docs.railway.app)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/)
- [WhiteNoise Documentation](http://whitenoise.evans.io)
