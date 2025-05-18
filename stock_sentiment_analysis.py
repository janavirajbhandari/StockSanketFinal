import json
import pandas as pd
from collections import defaultdict
import os
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
import numpy as np

def analyze_stock_sentiment():
    """Main function to analyze sentiment for all stocks"""
    print("🚀 Starting sentiment analysis...")
    
    # Create sentiment_data directory if it doesn't exist
    os.makedirs("sentiment_data", exist_ok=True)

    # Load the sentiment news CSV
    if not os.path.exists("stock_sentiment_news.csv"):
        print("❌ stock_sentiment_news.csv not found!")
        return
        
    df = pd.read_csv("stock_sentiment_news.csv")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")

    # Initialize sentiment analyzers
    vader = SentimentIntensityAnalyzer()

    def get_combined_sentiment(text, translated_text):
        """Get sentiment using both VADER and TextBlob, combining title and content"""
        try:
            # VADER sentiment
            vader_scores = vader.polarity_scores(translated_text)
            vader_compound = vader_scores['compound']
            
            # TextBlob sentiment
            blob = TextBlob(translated_text)
            textblob_polarity = blob.sentiment.polarity
            
            # Combine scores (weighted average)
            combined_score = (vader_compound * 0.7) + (textblob_polarity * 0.3)
            
            # Determine sentiment label
            if combined_score >= 0.05:
                sentiment = "positive"
            elif combined_score <= -0.05:
                sentiment = "negative"
            else:
                sentiment = "neutral"
                
            return {
                'polarity': combined_score,
                'sentiment': sentiment,
                'vader_scores': vader_scores,
                'textblob_polarity': textblob_polarity
            }
        except Exception as e:
            print(f"❌ Error analyzing sentiment: {e}")
            return {
                'polarity': 0,
                'sentiment': 'neutral',
                'vader_scores': {'neg': 0, 'neu': 1, 'pos': 0, 'compound': 0},
                'textblob_polarity': 0
            }

    # Process each news item
    print("📊 Processing news articles...")
    results = []
    for _, row in df.iterrows():
        # Combine title and content for better context
        original_text = f"{row['title']} {row.get('content', '')}"
        translated_text = f"{row.get('translated_title', '')} {row.get('translated_content', '')}"
        
        # Get sentiment
        sentiment_data = get_combined_sentiment(original_text, translated_text)
        
        results.append({
            'symbol': row['symbol'],
            'company': row['company'],
            'date': row['date_str'],
            'title': row['title'],
            'link': row['link'],
            'content': row.get('content', ''),
            'translated_title': row.get('translated_title', ''),
            'translated_content': row.get('translated_content', ''),
            'polarity': sentiment_data['polarity'],
            'sentiment': sentiment_data['sentiment'],
            'vader_scores': sentiment_data['vader_scores'],
            'textblob_polarity': sentiment_data['textblob_polarity']
        })

    # Convert to DataFrame for easier processing
    df_results = pd.DataFrame(results)

    # Generate sentiment data for each stock
    print("📈 Generating stock-wise sentiment data...")
    all_sentiment_data = {}

    for symbol in df_results['symbol'].unique():
        print(f"Processing {symbol}...")
        df_stock = df_results[df_results['symbol'] == symbol].copy()
        if df_stock.empty:
            continue
            
        total_articles = len(df_stock)
        sentiment_counts = df_stock['sentiment'].value_counts()
        
        # Calculate sentiment percentages
        sentiment_percents = {
            'positive': round((sentiment_counts.get('positive', 0) / total_articles) * 100, 2),
            'neutral': round((sentiment_counts.get('neutral', 0) / total_articles) * 100, 2),
            'negative': round((sentiment_counts.get('negative', 0) / total_articles) * 100, 2)
        }
        
        # Get most positive and negative articles
        df_sorted = df_stock.sort_values('polarity', ascending=False)
        top_positive = df_sorted.iloc[0] if len(df_sorted) > 0 else None
        top_negative = df_sorted.iloc[-1] if len(df_sorted) > 0 else None
        
        # Calculate moving averages
        df_stock['MA5'] = df_stock['polarity'].rolling(window=5).mean()
        df_stock['MA10'] = df_stock['polarity'].rolling(window=10).mean()
        
        # Prepare sentiment timeline
        timeline_data = df_stock.groupby('date').agg({
            'polarity': 'mean',
            'sentiment': lambda x: x.value_counts().index[0]
        }).reset_index()
        
        # Store stock sentiment data
        stock_data = {
            'symbol': symbol,
            'company': df_stock['company'].iloc[0],
            'total_articles': total_articles,
            'sentiment_distribution': sentiment_percents,
            'average_polarity': round(df_stock['polarity'].mean(), 4),
            'polarity_std': round(df_stock['polarity'].std(), 4),
            'top_positive_article': {
                'title': top_positive['title'],
                'translated_title': top_positive['translated_title'],
                'date': top_positive['date'],
                'link': top_positive['link'],
                'polarity': round(top_positive['polarity'], 4)
            } if top_positive is not None else None,
            'top_negative_article': {
                'title': top_negative['title'],
                'translated_title': top_negative['translated_title'],
                'date': top_negative['date'],
                'link': top_negative['link'],
                'polarity': round(top_negative['polarity'], 4)
            } if top_negative is not None else None,
            'timeline': timeline_data.to_dict('records'),
            'recent_articles': df_stock.sort_values('date', ascending=False).head(10).to_dict('records')
        }
        
        # Add to master data
        all_sentiment_data[symbol] = stock_data

    # Save combined sentiment data
    print("💾 Saving sentiment data...")
    with open("sentiment_data/sentiment_all_stocks.json", 'w', encoding='utf-8') as f:
        json.dump(all_sentiment_data, f, ensure_ascii=False, indent=2)

    print("✅ Sentiment analysis complete!")
    print(f"📊 Processed {len(df_results)} articles across {len(all_sentiment_data)} stocks")
    print("💾 Results saved in sentiment_data/sentiment_all_stocks.json")

if __name__ == "__main__":
    analyze_stock_sentiment() 