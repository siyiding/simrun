with open('data_fetcher.py', 'r') as f:
    content = f.read()

# Since we confirmed tx works well and fast without timeouts.
# Let's clean up any possible issue and push.

with open('data_fetcher.py', 'w') as f:
    f.write(content)
