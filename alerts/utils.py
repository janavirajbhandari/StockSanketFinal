from stocks.models import Stock  # Import your Stock model

def filter_tracked_symbols(alerts):
    symbols = set(Stock.objects.values_list("symbol", flat=True))
    return [a for a in alerts if a["symbol"] in symbols]
