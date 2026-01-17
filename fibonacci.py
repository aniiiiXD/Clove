def fibonacci_naive(n):
    """Naive recursive implementation of Fibonacci."""
    if n <= 1:
        return n
    return fibonacci_naive(n - 1) + fibonacci_naive(n - 2)

def fibonacci_dp(n):
    """Dynamic programming implementation of Fibonacci (bottom-up)."""
    if n <= 1:
        return n
    
    dp = [0] * (n + 1)
    dp[1] = 1
    
    for i in range(2, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
        
    return dp[n]

if __name__ == "__main__":
    test_val = 10
    print(f"Calculating Fibonacci for n={test_val}:")
    print(f"Naive Recursion Result: {fibonacci_naive(test_val)}")
    print(f"Dynamic Programming Result: {fibonacci_dp(test_val)}")
