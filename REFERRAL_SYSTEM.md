# Friend Referral System - Implementation Guide

## Overview
A complete friend referral program allowing users to invite friends via unique referral codes and earn credit (subscription discounts) when referred friends purchase packages. Credits can be used as discounts on future subscription purchases.

## Features Implemented

### 1. **Models**

#### ReferralCode
- **Purpose**: Store unique referral codes for each user
- **Auto-generated**: Automatically created for new users via signal
- **Fields**:
  - `code`: Unique 16-character alphanumeric code
  - `user`: OneToOne reference to User
  - `discount_percentage`: Optional promotional discount for referred friends (0-100%)
  - `description`: Optional marketing campaign description
  - `is_active`: Enable/disable code

#### ReferralEarnings
- **Purpose**: Track credit earned by referrers
- **Created**: Automatically when a referred friend's payment is verified (COMPLETED)
- **Fields**:
  - `referrer`: User who shared the code
  - `referee`: User who used the code
  - `referral_code`: The code that was used
  - `subscription_payment`: Link to the payment that triggered the earning
  - `subscription_package`: Package purchased
  - `package_price`: Price at time of purchase
  - `referral_percentage`: % of package that was credited to referrer
  - `credit_earned`: Actual credit amount (currency)
  - `is_recurring`: Flag for recurring monthly credits (future enhancement)
  - `month_number`: Which month of subscription this earning is for

#### UserCredit
- **Purpose**: Track credit balance per user
- **Auto-created**: Automatically created for new users
- **Fields**:
  - `user`: OneToOne reference
  - `balance`: Current available credit (THB)

#### ReferralTransaction
- **Purpose**: Ledger of all credit transactions
- **Auto-created**: Automatically when credit is added/deducted
- **Fields**:
  - `user`: User account
  - `transaction_type`: CREDIT or DEBIT
  - `amount`: THB amount
  - `description`: Reason for transaction
  - `referral_earning`: Link to earning (if applicable)
  - `subscription_payment`: Link to payment (if applicable)

#### SubscriptionPackage (Updated)
- **New Field**: `referral_percentage` (Decimal 0-100)
  - Percentage of package price earned as credit by referrer
  - Example: ฿4,990 package with 20% = ฿998 credit for referrer

#### SubscriptionPayment (Updated)
- **New Field**: `referral_code` (ForeignKey, optional)
  - Links payment to the referral code used
  - Enables tracking which code drove the conversion

---

## User Flows

### 1. **New User Registration**
```
User Registration → Signal Triggered → Auto-Create ReferralCode
                                    → Auto-Create UserCredit (balance=0)
```

### 2. **Friend Referral with Discount**
```
Referrer                          Referee
  │
  ├─ Share Code (e.g., ABC123XYZ)──→ Friend receives code
  │                                  │
  │                                  ├─ Go to subscription/payment
  │                                  ├─ Enter referral code at checkout
  │                                  ├─ See promotional discount applied
  │                                  └─ Upload payment slip
  │                                     │
  │                    Payment Verified (COMPLETED)
  │                           Signal Triggered
  │                                     │
  │                     Calculate referral % from package
  │                            │
  │              Create ReferralEarnings record
  │                            │
  │         ┌──────────────────┴────────────────┐
  │         ▼                                    ▼
  │    Get Referrer's                    Get Referee Info
  │    UserCredit Balance           (for ReferralEarnings)
  │         │
  │    Add Credit Amount            Create ReferralTransaction
  │    (via add_credit method)       (CREDIT type)
  │         │
  │    Update balance
  └─ Notify referrer of earned credit
```

### 3. **Using Credit on Renewal**
```
User wants to renew subscription
      │
      ├─ Go to payment page
      ├─ Select package
      ├─ System shows available credit: ฿998
      ├─ User applies credit if desired
      ├─ Discount applied to payment amount
      ├─ Upload payment slip for remaining balance
      │
      Payment Verified (COMPLETED)
            │
      ├─ Update UserCredit (deduct used amount)
      ├─ Create ReferralTransaction (DEBIT type)
      └─ Activate subscription
```

---

## Views & URLs

### Referral Dashboard
- **URL**: `/referral/dashboard/`
- **View**: `referral_dashboard()`
- **Access**: @login_required
- **Displays**:
  - User's referral code (copyable)
  - Current credit balance
  - Total earned & active count
  - Table of active referrals with:
    - Friend name & username
    - Package purchased
    - Package price paid
    - Credit earned for referrer
    - Signup date
    - Subscription status

### Payment Form
- **URL**: `/subscription/payment/submit/`
- **Method**: POST (form submission)
- **New Field**: `referral_code` (optional text input)
- **Logic**:
  1. Validate referral code if provided
  2. Check code is active and exists
  3. Check referrer ≠ referee
  4. Apply promotional discount if configured
  5. Store code in SubscriptionPayment record
  6. Calculate final payment amount

---

## Admin Interface

### ReferralCode Admin
- **Location**: Django Admin → Referral Codes
- **Features**:
  - List all codes with user, discount%, active status
  - Search by code, username, description
  - Edit discount_percentage and description per user
  - Set is_active to enable/disable code
  - Read-only code (auto-generated)

### ReferralEarnings Admin
- **Location**: Django Admin → Referral Earnings
- **Features**:
  - View all earnings with referrer, referee, credit amount
  - Filter by recurring flag, package, date
  - Search by username or referral code
  - Read-only (created automatically)
  - No manual add permission

### UserCredit Admin
- **Location**: Django Admin → User Credits
- **Features**:
  - View all credit balances
  - Sort by balance amount
  - Search by username
  - Read-only (created automatically)
  - No manual add permission

### ReferralTransaction Admin
- **Location**: Django Admin → Referral Transactions
- **Features**:
  - Ledger view of all transactions
  - Color-coded: green for CREDIT, red for DEBIT
  - Filter by type, date
  - Search by description
  - Read-only (created automatically)
  - No manual add permission

---

## Configuration

### Setting Referral Percentage per Package
```
Django Admin → Subscription Packages → Select Package
→ Referral Configuration → referral_percentage
→ Enter value (e.g., 20.00 for 20%)
```

### Adding Promotional Campaign to Referral Code
```
Django Admin → Referral Codes → Select User's Code
→ Marketing Campaign section:
  - discount_percentage: 10.00 (gives 10% discount to new user)
  - description: "New Year Special - 10% off first purchase"
→ Save
```

---

## How It Works - Examples

### Example 1: Basic Referral
```
Package: Premium (฿4,990/month, 20% referral_percentage)

Referrer shares code: ABC123XYZ

Friend uses code at checkout:
  - Original price: ฿4,990
  - No promotional discount configured
  - Friend pays: ฿4,990
  - Friend uploads payment slip

Payment verified (COMPLETED):
  - ReferralEarnings created: ฿4,990 × 20% = ฿998
  - Referrer's credit balance increased: ฿998
  - ReferralTransaction recorded
```

### Example 2: Referral with Promotional Campaign
```
Package: Premium (฿4,990/month, 20% referral_percentage)

Admin configured code ABC123XYZ with:
  - discount_percentage: 10.00
  - description: "Holiday Campaign - 10% off"

Friend uses code at checkout:
  - Original price: ฿4,990
  - Promotional discount (10%): -฿499
  - Friend pays: ฿4,491
  - Friend uploads payment slip for ฿4,491

Payment verified (COMPLETED):
  - Referral credit calculated on final amount: ฿4,491 × 20% = ฿898.20
  - Referrer's credit balance increased: ฿898.20
  - Admin notes record both discount and referral details
```

### Example 3: Using Credit for Renewal
```
Referrer has earned: ฿998 credit
Wants to renew Premium package (฿4,990)

At checkout:
  - Available credit shown: ฿998
  - System applies credit: ฿4,990 - ฿998 = ฿3,992 to pay
  - Referrer uploads payment slip for ฿3,992

Payment verified (COMPLETED):
  - UserCredit balance updated: ฿998 - ฿998 = ฿0
  - ReferralTransaction (DEBIT) created: -฿998
  - Subscription renewed with updated package
```

---

## Database Schema

```
ReferralCode
├── id (PK)
├── user_id (OneToOne FK → User, indexed)
├── code (CharField, unique, indexed)
├── discount_percentage (Decimal 5,2)
├── description (CharField)
├── is_active (Boolean)
├── created_at (DateTime, indexed)
└── updated_at (DateTime)

ReferralEarnings
├── id (PK)
├── referrer_id (FK → User, indexed)
├── referee_id (FK → User)
├── referral_code_id (FK → ReferralCode)
├── subscription_payment_id (FK → SubscriptionPayment, nullable)
├── subscription_package_id (FK → SubscriptionPackage)
├── package_price (Decimal 10,2)
├── referral_percentage (Decimal 5,2)
├── credit_earned (Decimal 10,2)
├── is_recurring (Boolean)
├── month_number (PositiveInteger)
├── is_active (Boolean)
├── created_at (DateTime, indexed)
├── updated_at (DateTime)
└── unique_together: (referrer, referee, subscription_payment)

UserCredit
├── id (PK)
├── user_id (OneToOne FK → User, indexed)
├── balance (Decimal 10,2)
├── is_active (Boolean)
├── created_at (DateTime, indexed)
└── updated_at (DateTime)

ReferralTransaction
├── id (PK)
├── user_id (FK → User, indexed)
├── transaction_type (CharField: CREDIT/DEBIT)
├── amount (Decimal 10,2)
├── description (TextField)
├── referral_earning_id (FK → ReferralEarnings, nullable)
├── subscription_payment_id (FK → SubscriptionPayment, nullable)
├── is_active (Boolean)
├── created_at (DateTime, indexed)
└── updated_at (DateTime)

SubscriptionPackage (Updated)
└── referral_percentage (Decimal 5,2) - NEW

SubscriptionPayment (Updated)
└── referral_code_id (FK → ReferralCode, nullable) - NEW
```

---

## Files Modified/Created

### New Files
- `/templates/referral/dashboard.html` - Referral program frontend

### Modified Files
1. **trading/models.py**
   - Added `referral_percentage` to SubscriptionPackage
   - Added `referral_code` FK to SubscriptionPayment
   - Added ReferralCode model
   - Added ReferralEarnings model
   - Added UserCredit model
   - Added ReferralTransaction model

2. **trading/views.py**
   - Modified `payment_submit_view()` to accept and validate referral codes
   - Added `referral_dashboard()` view
   - Added discount calculation logic

3. **trading/urls.py**
   - Added route: `/referral/dashboard/`

4. **trading/signals.py**
   - Added signal to auto-generate ReferralCode for new users
   - Added signal to auto-generate UserCredit for new users
   - Added signal to process referral earnings on payment completion

5. **trading/admin.py**
   - Added ReferralCodeAdmin
   - Added ReferralEarningsAdmin
   - Added UserCreditAdmin
   - Added ReferralTransactionAdmin
   - Updated SubscriptionPackageAdmin to include referral_percentage field

6. **templates/subscription/payment.html**
   - Added referral code input field

7. **templates/profile/index.html**
   - Added "Referral Program" menu link pointing to dashboard

---

## Migrations

Two migrations created:
- `0020_referralcode_referralearnings_and_more.py`
  - Creates ReferralCode, ReferralEarnings, UserCredit, ReferralTransaction tables
  - Adds referral_percentage to SubscriptionPackage

- `0021_subscriptionpayment_referral_code.py`
  - Adds referral_code FK to SubscriptionPayment

---

## Future Enhancements

1. **Recurring Monthly Credits**
   - Track which month the credit is for (month_number already in model)
   - Auto-process recurring credits on subscription renewal
   - Percentage decreases each month (e.g., 20%, 18%, 16%)

2. **Referral API Endpoints**
   - Create API for retrieving referral stats
   - Share referral link via URL structure
   - QR code generation for code sharing

3. **Credit Usage at Checkout**
   - UI to select whether to apply credit
   - Show discount preview before payment
   - Auto-apply credits if enabled

4. **Referral Bonuses**
   - Milestone bonuses (e.g., refer 3 friends → bonus ฿500)
   - Tiered rewards based on total referred spending
   - Bonus tracking and notifications

5. **Campaign Management**
   - Bulk operations to add discount to multiple codes
   - Campaign templates (% off, BOGO, etc.)
   - Time-limited campaigns with expiry dates

6. **Analytics & Reporting**
   - Referral conversion rates
   - Average credit earned per referrer
   - Top referrers leaderboard
   - Admin dashboard for program metrics

---

## Testing Checklist

- [ ] Auto-generate referral code for new user
- [ ] Auto-generate UserCredit balance for new user
- [ ] Validate referral code in payment form
- [ ] Reject invalid/inactive codes
- [ ] Reject self-referral attempts
- [ ] Apply promotional discount at checkout
- [ ] Create ReferralEarnings on payment completion
- [ ] Calculate credit correctly (% based)
- [ ] Add credit to referrer's balance
- [ ] Create ReferralTransaction records
- [ ] Display referral dashboard correctly
- [ ] Edit code discount_percentage in admin
- [ ] View referral earnings in admin (read-only)
- [ ] View credit balance in admin (read-only)
- [ ] View transaction ledger in admin
- [ ] Test with different package percentages
- [ ] Test with and without promotional discount
- [ ] Verify no duplicate ReferralEarnings created

---

## Notes

- All new models inherit from TimeStampedModel (auto created_at, updated_at)
- ReferralEarnings has unique_together constraint on (referrer, referee, subscription_payment) to prevent duplicates
- Referral signal uses post_save to ensure payment is fully saved before processing
- Credit add/deduct methods automatically create ReferralTransaction records
- Admin panels are read-only for auto-created data (no manual add permission)
- Referral codes are case-insensitive (uppercase conversion in template)
- Credit amounts are stored as Decimal for accuracy (no float rounding issues)

