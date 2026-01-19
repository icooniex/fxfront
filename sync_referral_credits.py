#!/usr/bin/env python
"""
Sync ReferralEarnings to UserCredit balances
Run this once to fix existing earnings that weren't credited
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fxfront.settings')
django.setup()

from trading.models import ReferralEarnings, UserCredit, ReferralTransaction
from decimal import Decimal

def sync_credits():
    # Get all earnings with credit > 0
    earnings = ReferralEarnings.objects.filter(credit_earned__gt=0)
    print(f'Found {earnings.count()} earnings with credit > 0\n')
    
    for earning in earnings:
        referrer = earning.referrer
        credit_balance, created = UserCredit.objects.get_or_create(user=referrer)
        
        # Check if this earning was already credited
        already_credited = ReferralTransaction.objects.filter(
            user=referrer,
            transaction_type='CREDIT',
            amount=earning.credit_earned,
            description__contains=earning.referee.username
        ).exists()
        
        if not already_credited:
            # Add credit
            credit_balance.add_credit(
                Decimal(str(earning.credit_earned)),
                f"Referral credit from {earning.referee.username} ({earning.subscription_package.name})"
            )
            print(f'✅ Added ฿{earning.credit_earned} to {referrer.username} (from {earning.referee.username})')
        else:
            print(f'⏭️  Already credited ฿{earning.credit_earned} to {referrer.username}')
    
    print('\n' + '='*50)
    print('Final UserCredit Balances:')
    print('='*50)
    for uc in UserCredit.objects.all():
        if uc.balance > 0:
            print(f'{uc.user.username}: ฿{uc.balance}')

if __name__ == '__main__':
    sync_credits()
