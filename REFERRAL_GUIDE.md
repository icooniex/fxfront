# Referral System - Quick Start Guide

## For End Users

### Access Referral Dashboard
1. Login to your account
2. Go to Profile Settings
3. Click "Referral Program" button
4. You'll see:
   - Your unique referral code (copyable)
   - Your current credit balance
   - List of friends who subscribed using your code
   - Credit earned from each referral

### Share Your Code
1. Copy your referral code from the dashboard
2. Share it with friends via:
   - WhatsApp, Telegram, Email
   - Social media
   - Word of mouth
3. Tell friends: "Use my code to get special offers when you subscribe!"

### Invite Friend with Discount
- If admin has configured a promotional offer on your code, friends will get an extra discount
- Example: "Use code ABC123XYZ for 10% off your first month!"

### Use Your Earned Credit
1. When renewing subscription, enter your referral code at checkout (if renewing)
2. Or simply wait for credits to accumulate
3. Use credits as discounts on future renewals:
   - Original price: ฿4,990
   - Available credit: ฿998
   - You pay: ฿3,992

---

## For Admin (Django Admin)

### Configure Referral Earnings per Package
1. Go to Django Admin
2. Select Subscription Packages
3. Open a package you want to enable referrals for
4. Scroll to "Referral Configuration" section
5. Enter `referral_percentage` (e.g., 20 for 20%)
6. Save

### Set Up Marketing Campaign on a Referral Code
1. Go to Django Admin
2. Select Referral Codes
3. Find the user's code you want to promote
4. In "Marketing Campaign" section:
   - Set `discount_percentage` (e.g., 10 for 10% off)
   - Set `description` (e.g., "Holiday Special - Get 10% off!")
5. Ensure `is_active` is checked
6. Save

### Monitor Referral Activity
- **View Earnings**: Django Admin → Referral Earnings
- **View Credit Balances**: Django Admin → User Credits  
- **View Transaction Log**: Django Admin → Referral Transactions
- Filter by date, user, type to see activity

### Edit a Referral Code
1. Go to Django Admin → Referral Codes
2. Click on the code you want to modify
3. Update:
   - `discount_percentage`: Change promotional discount
   - `description`: Update campaign name/description
   - `is_active`: Disable/enable code
4. Save (the code itself cannot be changed, it's auto-generated)

### Troubleshooting
- **User didn't get credit**: Check if:
  - Package has `referral_percentage > 0`
  - Payment status is "COMPLETED"
  - Code was used by a different user (not same person)
- **User can't use code**: Check if:
  - Code `is_active` is checked
  - Code is not their own code (self-referral not allowed)
  - Code exists in system

---

## Technical Reference

### Models Summary
- **ReferralCode**: User's referral code + optional promotional offer
- **ReferralEarnings**: Credit earned per referral (auto-created)
- **UserCredit**: User's credit balance (auto-created, auto-updated)
- **ReferralTransaction**: Ledger of credit additions/deductions (auto-created)

### Signal Flow
```
New User Created
  → Auto-create ReferralCode (unique code generated)
  → Auto-create UserCredit (balance = 0)

Payment Status → COMPLETED
  → Check if referral_code is set
  → Get referrer from code
  → Calculate credit: payment_amount × package.referral_percentage / 100
  → Create ReferralEarnings record
  → Add credit to referrer's UserCredit balance
  → Create ReferralTransaction (CREDIT type)
```

### View URLs
- Referral Dashboard: `/referral/dashboard/`
- Payment with Code: `/subscription/payment/submit/` (POST with referral_code parameter)

### Admin Pages
- Referral Codes: `/admin/trading/referralcode/`
- Referral Earnings: `/admin/trading/referralearnings/`
- User Credits: `/admin/trading/usercredit/`
- Referral Transactions: `/admin/trading/referraltransaction/`

---

## Example Scenarios

### Scenario 1: Basic Referral (No Promotion)
```
Setup:
  Package: Premium (฿4,990, referral_percentage=20%)
  Code: ABC123XYZ (no discount configured)

Friend's Action:
  → Use code ABC123XYZ
  → Pay ฿4,990 (no discount)

Referrer's Benefit:
  → Earns: ฿4,990 × 20% = ฿998
  → Credit appears in account immediately after payment verified
```

### Scenario 2: Referral with Holiday Campaign
```
Setup:
  Package: Premium (฿4,990, referral_percentage=20%)
  Code: XYZ789ABC (discount_percentage=10%, description="Holiday 10% Off")

Friend's Action:
  → Uses code XYZ789ABC at checkout
  → Sees: Original ฿4,990 - 10% (฿499) = ฿4,491 to pay
  → Pays ฿4,491

Referrer's Benefit:
  → Earns: ฿4,491 × 20% = ฿898.20 credit
  → (Calculation is based on the discounted price paid)
```

### Scenario 3: Using Accumulated Credit
```
Situation:
  User has earned ฿998 + ฿898 + ฿799 = ฿2,695 total credit

Renewal Time:
  → Package costs ฿4,990
  → System shows: Available credit ฿2,695
  → User uses credit: ฿4,990 - ฿2,695 = ฿2,295 to pay
  → Uploads payment slip for ฿2,295

Result:
  → Credit balance after renewal: ฿0
  → Subscription renewed for another month
```

---

## Configuration Examples

### Recommended Settings by Market

#### Aggressive Growth
```
Package: Starter (฿1,990)
referral_percentage: 25% (฿497.50 per referral)

Package: Premium (฿4,990)  
referral_percentage: 25% (฿1,247.50 per referral)

Typical Campaign:
Code discount: 10-15% to incentivize sign-ups
```

#### Conservative/Stable
```
Package: Starter (฿1,990)
referral_percentage: 15% (฿298.50 per referral)

Package: Premium (฿4,990)
referral_percentage: 20% (฿998 per referral)

Typical Campaign:
Code discount: 5-10% or no discount
```

#### Premium/High-Value
```
Package: Enterprise (฿14,990)
referral_percentage: 10% (฿1,499 per referral)

Typical Campaign:
Code discount: 0% (high-value customers already sold on product)
```

---

## Common Questions

**Q: Can a user refer themselves?**
A: No, the system prevents self-referrals. Referrer must be different from referee.

**Q: What happens if the referred friend doesn't pay?**
A: No credit is earned. Earnings are only created when payment is verified (COMPLETED status).

**Q: Can users share their referral code publicly?**
A: Yes! The system supports any distribution method. Make sure admin approves any public campaigns.

**Q: What if a friend uses the code but then cancels?**
A: The credit was already given. Cancellation doesn't reverse the earning. Consider implementing a "refund" scenario if needed.

**Q: Can the referral code be changed?**
A: The code itself is auto-generated and cannot be changed. But admin can edit the promotional discount/description at any time.

**Q: Is there a time limit on using a referral code?**
A: No built-in time limit. Codes are active until admin sets `is_active=False`.

**Q: Can credits expire?**
A: Currently no expiration. Credits accumulate indefinitely. Consider adding expiry logic if needed.

**Q: Are monthly recurring credits supported?**
A: Model fields are ready (is_recurring, month_number) but logic not yet implemented. Planned for future release.

---

## Support & Debugging

### Common Issues

**Issue**: Friend says they got no discount when using code
- Check: Is the code `is_active=True` in admin?
- Check: Is `discount_percentage > 0` set?
- Check: Did they enter code correctly? (Case-insensitive but must match)

**Issue**: Referrer didn't receive credit after payment
- Check: Payment status is "COMPLETED"?
- Check: Package has `referral_percentage > 0`?
- Check: Different user referred (no self-referral)?
- Check: No duplicate ReferralEarnings? (should be unique by referrer+referee+payment)

**Issue**: User can't see referral code
- Check: Is UserProfile for this user active?
- Check: Does ReferralCode exist? (should auto-create)
- If missing, manually create one in admin with unique code

**Debug Steps**:
1. Check Django Admin → User Credits (verify balance)
2. Check Django Admin → Referral Transactions (see transaction log)
3. Check Django Admin → Referral Earnings (see earnings records)
4. Check SubscriptionPayment records (verify referral_code_id is set)

