use std::collections::HashMap;

/// Calculates the nth Fibonacci number using a memoization HashMap.
fn fib(n: u32, memo: &mut HashMap<u32, u64>) -> u64 {
    // Check if the result is already computed and stored in the map.
    if let Some(&val) = memo.get(&n) {
        return val;
    }

    // Compute the value recursively.
    let val = match n {
        0 => 0,
        1 => 1,
        _ => fib(n - 1, memo) + fib(n - 2, memo),
    };

    // Store the computed value in the memoization map.
    memo.insert(n, val);
    val
}

/// A convenient wrapper function that initializes the memoization HashMap.
pub fn fibonacci(n: u32) -> u64 {
    let mut memo = HashMap::new();
    fib(n, &mut memo)
}

fn main() {
    println!("--- Fibonacci with HashMap Memoization ---");
    
    // 1. Using the one-off wrapper function
    println!("Using the one-off wrapper function:");
    let val_10 = fibonacci(10);
    println!("fibonacci(10) = {}\n", val_10);
    
    // 2. Reusing a single shared memoization map for sequential calls
    println!("Using a shared memoization map (ideal for multiple calculations):");
    let mut shared_memo = HashMap::new();
    for i in 0..=10 {
        let result = fib(i, &mut shared_memo);
        println!("fib({}) = {}", i, result);
    }
}
