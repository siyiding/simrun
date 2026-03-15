import akshare as ak

# Attempt to fetch code data using multiple methods and print length
# Some methods don't fetch K lines, just codes

print("Testing stock_info_a_code_name...")
try:
    df = ak.stock_info_a_code_name()
    print("Found rows:", len(df))
    print(df.head())
except Exception as e:
    print("Error:", e)

