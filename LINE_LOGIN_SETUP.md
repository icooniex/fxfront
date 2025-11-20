# คู่มือการตั้งค่า LINE Login

## ขั้นตอนการตั้งค่า

### 1. สร้าง LINE Login Channel

1. ไปที่ [LINE Developers Console](https://developers.line.biz/console/)
2. Login ด้วยบัญชี LINE ของคุณ
3. คลิก "Create a new provider" (ถ้ายังไม่มี)
4. คลิก "Create a new channel"
5. เลือก "LINE Login"
6. กรอกข้อมูล:
   - Channel name: `FX Bot Monitor`
   - Channel description: `FX Trading Bot Monitoring System`
   - App types: เลือก `Web app`
7. คลิก "Create"

### 2. ตั้งค่า Channel

หลังสร้าง Channel แล้ว:

1. ไปที่ Tab **"Basic settings"**:
   - คัดลอก **Channel ID**
   - คัดลอก **Channel secret**

2. ไปที่ Tab **"LINE Login"**:
   - **Callback URL**: เพิ่ม URL ดังนี้
     - Development: `http://localhost:8000/auth/line/callback/`
     - Production: `https://your-app-name.up.railway.app/auth/line/callback/`

### 3. ตั้งค่า Environment Variables

#### ในเครื่อง (Local Development):

แก้ไขไฟล์ `.env`:
```env
LINE_CHANNEL_ID=your-channel-id-here
LINE_CHANNEL_SECRET=your-channel-secret-here
LINE_CALLBACK_URL=http://localhost:8000/auth/line/callback/
```

#### บน Railway:

ไปที่ Railway Dashboard → Variables และเพิ่ม:
```bash
LINE_CHANNEL_ID=your-channel-id-here
LINE_CHANNEL_SECRET=your-channel-secret-here
LINE_CALLBACK_URL=https://your-app-name.up.railway.app/auth/line/callback/
```

### 4. รัน Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. ทดสอบ LINE Login

1. รัน server: `python manage.py runserver`
2. เปิด browser ไปที่ `http://localhost:8000/login/`
3. คลิก "เข้าสู่ระบบด้วย LINE"
4. ระบบจะ redirect ไปยัง LINE OAuth
5. Login ด้วย LINE
6. ระบบจะ redirect กลับมาและ login อัตโนมัติ

## การทำงาน

### สำหรับ User ที่มีบัญชีแล้ว:
- คลิก "เข้าสู่ระบบด้วย LINE"
- Login ด้วย LINE
- ระบบจะตรวจสอบ LINE User ID
- Login เข้าสู่ระบบอัตโนมัติ

### สำหรับ User ใหม่:
- คลิก "เข้าสู่ระบบด้วย LINE"
- Login ด้วย LINE
- ระบบจะเก็บข้อมูล LINE ไว้ใน session
- Redirect ไปหน้าสมัครสมาชิก
- กรอกข้อมูลเพิ่มเติม (username, password, ชื่อ-นามสกุล)
- สมัครสมาชิกสำเร็จ และ login อัตโนมัติ

## ข้อมูลที่เก็บจาก LINE

- `line_uuid`: LINE User ID (ใช้เป็น unique identifier)
- `line_display_name`: ชื่อที่แสดงใน LINE
- `line_picture_url`: รูปโปรไฟล์จาก LINE

## Troubleshooting

### Error: "LINE Login ยังไม่ได้ตั้งค่า"
- ตรวจสอบว่าตั้งค่า `LINE_CHANNEL_ID` ใน environment variables แล้ว

### Error: "การเข้าสู่ระบบด้วย LINE ล้มเหลว"
- ตรวจสอบ `LINE_CALLBACK_URL` ว่าตรงกับที่ตั้งใน LINE Developers Console
- ตรวจสอบ `LINE_CHANNEL_SECRET` ว่าถูกต้อง

### Callback URL ไม่ตรงกัน
- ตรวจสอบใน LINE Developers Console → LINE Login → Callback URL
- ต้องตรงกับ `LINE_CALLBACK_URL` ใน environment variables

## Security

- ✅ ใช้ state parameter เพื่อป้องกัน CSRF attack
- ✅ เก็บ LINE User ID เป็น unique identifier
- ✅ ไม่เก็บ access token (ใช้แค่ตอน OAuth flow)
- ✅ ตรวจสอบ state ก่อน process callback ทุกครั้ง
