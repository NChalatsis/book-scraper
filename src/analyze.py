"""Quick analysis of the scraped data: average price per star rating."""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

df = pd.read_csv("data/books.csv")
summary = df.groupby("rating")["price_gbp"].agg(["count", "mean"]).round(2)
print(summary)
print(f"\nBooks: {len(df)} | In stock: {df['in_stock'].mean():.0%}")

Path("images").mkdir(exist_ok=True)
summary["mean"].plot(kind="bar", color="#2a6f97", title="Average price by rating")
plt.xlabel("Star rating")
plt.ylabel("Average price (£)")
plt.tight_layout()
plt.savefig("images/price_by_rating.png", dpi=120)
print("Chart saved to images/price_by_rating.png")
