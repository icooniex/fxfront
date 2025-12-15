"""
LINE Messaging API Notification Service

This module handles sending notifications to users via LINE Messaging API.
Users must have connected their LINE account via LINE Login first.
"""

import requests
from django.conf import settings
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class LineNotificationService:
    """Service for sending LINE notifications using LINE Messaging API"""
    
    MESSAGING_API_URL = "https://api.line.me/v2/bot/message/push"
    
    def __init__(self):
        self.channel_access_token = getattr(settings, 'LINE_CHANNEL_ACCESS_TOKEN', '')
        
        if not self.channel_access_token:
            logger.warning("LINE_CHANNEL_ACCESS_TOKEN is not configured")
    
    def send_message(self, line_user_id: str, message: str) -> Dict[str, Any]:
        """
        Send a text message to a LINE user
        
        Args:
            line_user_id: LINE user ID (from UserProfile.line_uuid)
            message: Text message to send
            
        Returns:
            Dict with 'success' (bool), 'message' (str), and optional 'error'
        """
        if not self.channel_access_token:
            return {
                'success': False,
                'message': 'LINE Messaging API not configured',
                'error': 'Missing LINE_CHANNEL_ACCESS_TOKEN'
            }
        
        if not line_user_id or line_user_id.startswith('temp_'):
            return {
                'success': False,
                'message': 'User has not connected LINE account',
                'error': 'Invalid or temporary LINE user ID'
            }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.channel_access_token}'
        }
        
        payload = {
            'to': line_user_id,
            'messages': [
                {
                    'type': 'text',
                    'text': message
                }
            ]
        }
        
        try:
            response = requests.post(
                self.MESSAGING_API_URL,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"LINE notification sent successfully to {line_user_id[:8]}...")
                return {
                    'success': True,
                    'message': 'Notification sent successfully'
                }
            else:
                error_data = response.json() if response.text else {}
                error_message = error_data.get('message', 'Unknown error')
                logger.error(f"Failed to send LINE notification: {response.status_code} - {error_message}")
                return {
                    'success': False,
                    'message': 'Failed to send notification',
                    'error': error_message,
                    'status_code': response.status_code
                }
        
        except requests.RequestException as e:
            logger.error(f"LINE notification request error: {str(e)}")
            return {
                'success': False,
                'message': 'Network error while sending notification',
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error sending LINE notification: {str(e)}")
            return {
                'success': False,
                'message': 'Unexpected error',
                'error': str(e)
            }
    
    def send_flex_message(self, line_user_id: str, alt_text: str, flex_content: Dict) -> Dict[str, Any]:
        """
        Send a Flex Message to a LINE user
        
        Args:
            line_user_id: LINE user ID
            alt_text: Alternative text for notifications
            flex_content: Flex Message JSON content
            
        Returns:
            Dict with 'success' (bool), 'message' (str), and optional 'error'
        """
        if not self.channel_access_token:
            return {
                'success': False,
                'message': 'LINE Messaging API not configured',
                'error': 'Missing LINE_CHANNEL_ACCESS_TOKEN'
            }
        
        if not line_user_id or line_user_id.startswith('temp_'):
            return {
                'success': False,
                'message': 'User has not connected LINE account',
                'error': 'Invalid or temporary LINE user ID'
            }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.channel_access_token}'
        }
        
        payload = {
            'to': line_user_id,
            'messages': [
                {
                    'type': 'flex',
                    'altText': alt_text,
                    'contents': flex_content
                }
            ]
        }
        
        try:
            response = requests.post(
                self.MESSAGING_API_URL,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"LINE Flex Message sent successfully to {line_user_id[:8]}...")
                return {
                    'success': True,
                    'message': 'Flex message sent successfully'
                }
            else:
                error_data = response.json() if response.text else {}
                error_message = error_data.get('message', 'Unknown error')
                logger.error(f"Failed to send LINE Flex Message: {response.status_code} - {error_message}")
                return {
                    'success': False,
                    'message': 'Failed to send flex message',
                    'error': error_message,
                    'status_code': response.status_code
                }
        
        except requests.RequestException as e:
            logger.error(f"LINE Flex Message request error: {str(e)}")
            return {
                'success': False,
                'message': 'Network error while sending flex message',
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error sending LINE Flex Message: {str(e)}")
            return {
                'success': False,
                'message': 'Unexpected error',
                'error': str(e)
            }


# Trading notification helpers
class TradingNotifications:
    """Helper class for formatting trading-related notifications"""
    
    def __init__(self):
        self.line_service = LineNotificationService()
    
    def notify_new_trade(self, user_profile, trade_data: Dict) -> Dict[str, Any]:
        """
        Notify user about a new trade being opened
        
        Args:
            user_profile: UserProfile instance
            trade_data: Dict with trade information (symbol, type, entry_price, lot_size, etc.)
        """
        if not user_profile.is_line_connected():
            return {'success': False, 'message': 'LINE not connected'}
        
        symbol = trade_data.get('symbol', 'N/A')
        position_type = trade_data.get('position_type', 'N/A')
        entry_price = trade_data.get('entry_price', 'N/A')
        lot_size = trade_data.get('lot_size', 'N/A')
        account_name = trade_data.get('account_name', 'Trading Account')
        
        message = f"""🔔 เทรดใหม่เปิด!

📊 บัญชี: {account_name}
💱 คู่เงิน: {symbol}
📈 ประเภท: {position_type}
💰 ราคาเข้า: {entry_price}
📦 Lot Size: {lot_size}

ดูรายละเอียดเพิ่มเติมได้ที่แอป FX Bot Monitor"""
        
        return self.line_service.send_message(user_profile.line_uuid, message)
    
    def notify_trade_closed(self, user_profile, trade_data: Dict) -> Dict[str, Any]:
        """
        Notify user about a trade being closed
        
        Args:
            user_profile: UserProfile instance
            trade_data: Dict with trade information (symbol, profit_loss, close_reason, etc.)
        """
        if not user_profile.is_line_connected():
            return {'success': False, 'message': 'LINE not connected'}
        
        symbol = trade_data.get('symbol', 'N/A')
        profit_loss = trade_data.get('profit_loss', 0)
        close_reason = trade_data.get('close_reason', 'Manual')
        account_name = trade_data.get('account_name', 'Trading Account')
        
        # Format profit/loss with emoji
        if profit_loss > 0:
            pnl_emoji = "✅"
            pnl_text = f"+${profit_loss:.2f}"
        elif profit_loss < 0:
            pnl_emoji = "❌"
            pnl_text = f"-${abs(profit_loss):.2f}"
        else:
            pnl_emoji = "➖"
            pnl_text = f"${profit_loss:.2f}"
        
        message = f"""🔔 เทรดปิด!

📊 บัญชี: {account_name}
💱 คู่เงิน: {symbol}
{pnl_emoji} กำไร/ขาดทุน: {pnl_text}
🏁 สาเหตุ: {close_reason}

ดูรายละเอียดเพิ่มเติมได้ที่แอป FX Bot Monitor"""
        
        return self.line_service.send_message(user_profile.line_uuid, message)
    
    def notify_daily_summary(self, user_profile, summary_data: Dict) -> Dict[str, Any]:
        """
        Send daily trading summary to user
        
        Args:
            user_profile: UserProfile instance
            summary_data: Dict with daily summary (total_trades, profit_loss, win_rate, etc.)
        """
        if not user_profile.is_line_connected():
            return {'success': False, 'message': 'LINE not connected'}
        
        total_trades = summary_data.get('total_trades', 0)
        profit_loss = summary_data.get('profit_loss', 0)
        win_rate = summary_data.get('win_rate', 0)
        account_name = summary_data.get('account_name', 'Trading Account')
        
        # Format profit/loss
        if profit_loss > 0:
            pnl_emoji = "✅"
            pnl_text = f"+${profit_loss:.2f}"
        elif profit_loss < 0:
            pnl_emoji = "❌"
            pnl_text = f"-${abs(profit_loss):.2f}"
        else:
            pnl_emoji = "➖"
            pnl_text = f"${profit_loss:.2f}"
        
        message = f"""📊 สรุปผลวันนี้

📈 บัญชี: {account_name}
🔢 จำนวนเทรด: {total_trades}
{pnl_emoji} กำไร/ขาดทุน: {pnl_text}
🎯 Win Rate: {win_rate:.1f}%

ดูรายละเอียดเพิ่มเติมได้ที่แอป FX Bot Monitor"""
        
        return self.line_service.send_message(user_profile.line_uuid, message)
    
    def notify_bot_status_change(self, user_profile, status_data: Dict) -> Dict[str, Any]:
        """
        Notify user about bot status changes
        
        Args:
            user_profile: UserProfile instance
            status_data: Dict with status information (account_name, status, reason, etc.)
        """
        if not user_profile.is_line_connected():
            return {'success': False, 'message': 'LINE not connected'}
        
        account_name = status_data.get('account_name', 'Trading Account')
        status = status_data.get('status', 'Unknown')
        reason = status_data.get('reason', '')
        
        status_emoji = {
            'ACTIVE': '✅',
            'PAUSED': '⏸️',
            'DOWN': '❌',
            'ERROR': '⚠️'
        }.get(status, '🔔')
        
        message = f"""{status_emoji} สถานะ Bot เปลี่ยน!

📊 บัญชี: {account_name}
📡 สถานะ: {status}"""
        
        if reason:
            message += f"\n💬 เหตุผล: {reason}"
        
        message += "\n\nดูรายละเอียดเพิ่มเติมได้ที่แอป FX Bot Monitor"
        
        return self.line_service.send_message(user_profile.line_uuid, message)
    
    def notify_account_alert(self, user_profile, alert_data: Dict) -> Dict[str, Any]:
        """
        Send account alerts (e.g., low balance, high drawdown, etc.)
        
        Args:
            user_profile: UserProfile instance
            alert_data: Dict with alert information
        """
        if not user_profile.is_line_connected():
            return {'success': False, 'message': 'LINE not connected'}
        
        account_name = alert_data.get('account_name', 'Trading Account')
        alert_type = alert_data.get('alert_type', 'Warning')
        alert_message = alert_data.get('message', 'Alert notification')
        
        message = f"""⚠️ แจ้งเตือนบัญชี!

📊 บัญชี: {account_name}
🔔 ประเภท: {alert_type}
💬 {alert_message}

ดูรายละเอียดเพิ่มเติมได้ที่แอป FX Bot Monitor"""
        
        return self.line_service.send_message(user_profile.line_uuid, message)


# Singleton instances
line_notification_service = LineNotificationService()
trading_notifications = TradingNotifications()
