# SSL Connection Error Fix

## Problem
Bot connections were being reset during SSL handshake and while reading responses:

**Error 1: Connection reset during SSL handshake:**
```
ConnectionResetError: [WinError 10054] An existing connection was forcibly closed by the remote host
urllib3.exceptions.ProtocolError: ('Connection aborted.', ConnectionResetError(...))
```

**Error 2: Connection reset while reading batch response:**
```
ChunkedEncodingError: Connection broken: ConnectionResetError(10054, ...)
# Occurs during batch_update_orders endpoint
```

## Root Cause
The issue was caused by:
1. **Default Gunicorn timeout** (30s) was too short for SSL handshakes under load
2. **Missing SSL proxy headers** - Django wasn't properly configured to handle SSL termination from Railway's reverse proxy
3. **No keep-alive connections** - Each bot request was establishing a new SSL connection
4. **Connection pool exhaustion** - Database connections weren't being managed efficiently
5. **Inefficient batch processing** - Sequential processing of orders with N+1 query problem
6. **Large response bodies** - Returning all order IDs caused memory/bandwidth issues

## Changes Made

### 1. Gunicorn Configuration ([gunicorn.conf.py](gunicorn.conf.py))
Created production-ready Gunicorn configuration:
- **Timeout increased to 120s** (from 30s default) to prevent premature connection termination
- **Keep-alive connections enabled** (5s) to reuse SSL connections and reduce handshake overhead
- **Proper SSL proxy headers** configured to trust Railway's X-Forwarded-Proto
- **Worker timeout and graceful shutdown** configured for stability
- **Request limits** to prevent memory leaks (max_requests=1000)
- **Request size limits increased** for batch operations (limit_request_field_size=8190)

### 2. Django Settings Updates ([fxfront/settings.py](fxfront/settings.py))
Added production security and connection resilience:
- **SECURE_PROXY_SSL_HEADER** - Trust X-Forwarded-Proto from Railway proxy
- **Secure cookies** (SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE) for HTTPS
- **HSTS headers** for enhanced security
- **Database connection timeout** (10s) to fail fast on connection issues
- **Connection pooling** maintained at 600s (conn_max_age)

### 3. Procfile Update
Modified to use new Gunicorn configuration:
```
web: gunicorn fxfront.wsgi --config gunicorn.conf.py --log-file -
```

### 4. Batch Endpoint Optimization ([trading/api/views.py](trading/api/views.py))
Optimized `batch_create_update_orders` to prevent timeouts and connection resets:
- **Batch size limit** (max 500 orders) to prevent worker timeout
- **Bulk database queries** - Pre-fetch all accounts and orders in 2-3 queries instead of N queries
- **Reduced response size** - Only return summary stats, not all order IDs
- **Eliminated N+1 query problem** - Cache accounts and orders before processing
- **Failed orders limit** - Only return details for ≤50 failures to prevent large responses

## Deployment Instructions

### For Railway (Current Deployment)

1. **Commit and push changes:**
   ```bash
   git add gunicorn.conf.py fxfront/settings.py Procfile SSL_FIX.md trading/api/views.py
   git commit -m "Fix: Optimize batch endpoint and prevent SSL connection resets"
   git push origin main
   ```

2. **Railway will automatically redeploy** with the new configuration

3. **Verify the fix:**
   - Check Railway logs for successful startup
   - Bot should now connect without SSL errors
   - Monitor for "Connection aborted" errors (should be resolved)

### Environment Variables to Check

Ensure these are set in Railway:
```bash
DEBUG=False
ALLOWED_HOSTS=.railway.app,your-domain.com
CSRF_TRUSTED_ORIGINS=https://your-domain.railway.app
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://...  # Automatically set by Railway
```

### For Other Deployments

If deploying to other platforms (Heroku, DigitalOcean, etc.):

1. Ensure your reverse proxy/load balancer sets these headers:
   - `X-Forwarded-Proto: https`
   - `X-Forwarded-For: <client-ip>`
   - `X-Forwarded-Host: <your-domain>`

2. Adjust `gunicorn.conf.py` if needed:
   - `bind` address (currently 0.0.0.0:$PORT)
   - `workers` count based on your server resources
   - `timeout` if you have slower network conditions

## Testing the Fix

### From Bot Side:
The bot should successfully connect and send heartbeats without SSL errors.

### Manual API Test:
```bash
# Test heartbeat endpoint
curl -X POST https://your-domain.railway.app/api/bot/heartbeat/ \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "mt5_account_id": "12345678",
    "bot_status": "ACTIVE",
    "current_balance": 10000.00
  }'
```

Expected response:
```json
{
  "status": "success",
  "message": "Heartbeat received",
  "should_continue": true,
  "bot_status": "ACTIVE",
  ...
}
```

## Monitoring

After deployment, monitor:

1. **Railway Logs** - Check for:
   - `[INFO] Booting worker with pid: ...` (successful worker starts)
   - No "Worker timeout" messages
   - No "Connection reset" errors

2. **Bot Logs** - Should show:
   - Successful heartbeat responses
   - No SSL/TLS errors
   - No connection timeouts

3. **Response Times** - Should see:
   - Faster API responses due to connection keep-alive
   - Reduced SSL handshake overhead

## Performance Improvements

Expected improvements:
- **Reduced SSL handshake overhead** - Keep-alive connections reuse SSL sessions
- **Better connection stability** - Longer timeouts prevent premature disconnections
- **Improved throughput** - More workers and efficient connection pooling
- **Graceful degradation** - Better error handling and connection resilience

## Rollback Plan

If issues occur, rollback by reverting these files:
```bash
git revert HEAD
git push origin main
```

This will restore the previous Gunicorn configuration.

## Additional Recommendations

### For Bot Application:
1. **Add retry logic** with exponential backoff:
   ```python
   from requests.adapters import HTTPAdapter
   from urllib3.util.retry import Retry
   
   session = requests.Session()
   retry = Retry(
       total=3, 
       backoff_factor=1, 
       status_forcelist=[502, 503, 504],
       allowed_methods=["POST", "GET"]
   )
   adapter = HTTPAdapter(max_retries=retry)
   session.mount('https://', adapter)
   ```

2. **Implement connection pooling**:
   ```python
   session = requests.Session()
   session.headers.update({'Authorization': f'Bearer {API_KEY}'})
   # Reuse session for all requests
   ```

3. **Add timeout to requests**:
   ```python
   response = session.post(url, json=data, timeout=(10, 30))
   # (connect_timeout, read_timeout)
   ```

4. **Batch size limits** - Split large batches:
   ```python
   BATCH_SIZE = 500  # Server limit
   
   def send_orders_in_batches(orders):
       for i in range(0, len(orders), BATCH_SIZE):
           batch = orders[i:i+BATCH_SIZE]
           try:
               response = session.post(
                   f"{API_BASE_URL}/bot/orders/batch/",
                   json=batch,
                   timeout=(10, 60)  # 60s for batch processing
               )
               response.raise_for_status()
           except requests.exceptions.RequestException as e:
               logger.error(f"Batch {i//BATCH_SIZE} failed: {e}")
               # Handle retry or skip
   ```

5. **Stream large responses** (if needed):
   ```python
   response = session.post(url, json=data, stream=True)
   # Process response in chunks if very large
   ```

### For Server Monitoring:
1. Set up Railway metrics monitoring
2. Add error tracking (e.g., Sentry)
3. Monitor worker memory usage
4. Track API response times

## Related Files
- [gunicorn.conf.py](gunicorn.conf.py) - Gunicorn configuration
- [fxfront/settings.py](fxfront/settings.py) - Django settings
- [Procfile](Procfile) - Railway process configuration
- [DEPLOYMENT.md](DEPLOYMENT.md) - General deployment guide
