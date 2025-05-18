from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .utils import get_live_market_data  # Import your existing market data function

@login_required
def get_market_data(request, symbol):
    try:
        # Fetch market data using your existing function
        market_data = get_live_market_data(symbol)
        
        # Format the response data
        response_data = {
            'company': market_data.get('company_name', 'N/A'),
            'market_cap': market_data.get('market_cap', 'N/A'),
            'price': market_data.get('last_traded_price', 'N/A'),
            'change': market_data.get('percent_change', 'N/A'),
            'volume': market_data.get('total_trades', 'N/A'),
            'turnover': market_data.get('turnover', 'N/A')
        }
        
        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def stock_table_partial(request):
    symbol = request.GET.get('symbol')
    if not symbol:
        return JsonResponse({'error': 'Symbol is required'})
    
    try:
        # Fetch market data for the table
        market_data = get_live_market_data(symbol)
        
        # Format the response data
        response_data = {
            'company': market_data.get('company_name', 'N/A'),
            'market_cap': market_data.get('market_cap', 'N/A'),
            'price': market_data.get('price', 'N/A'),
            'change': market_data.get('change', 'N/A'),
            'volume': market_data.get('volume', 'N/A'),
            'turnover': market_data.get('turnover', 'N/A')
        }
        
        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({'error': str(e)}) 