# Kairo Phantom — Confidence Calibration Report

## Calibration Method: Platt Scaling

**Coefficients:** slope=0.88, intercept=0.06  
**Abstention Threshold:** 60%  
**Expected Calibration Error (ECE):** 0.1386  

## Reliability Diagram Data

| Bin | Mean Confidence | Empirical Accuracy | Δ (Cal. Error) | Samples |
|-----|----------------|--------------------|----------------|---------|
|  1 | 15.8% | 16.7% | 0.8% | 6 |
|  2 | 24.9% | 28.6% | 3.7% | 7 |
|  3 | 34.3% | 50.0% | 15.7% | 10 |
|  4 | 43.8% | 60.0% | 16.2% | 10 |
|  5 | 54.0% | 86.7% | 32.6% | 15 |
|  6 | 65.2% | 83.3% | 18.2% | 12 |
|  7 | 74.8% | 81.2% | 6.4% | 16 |
|  8 | 85.1% | 94.7% | 9.7% | 19 |
|  9 | 91.7% | 100.0% | 8.3% | 5 |

## Interpretation

A perfectly calibrated model has mean confidence ≈ empirical accuracy per bin.
ECE < 5% is considered well-calibrated. Current ECE = **13.86%**.

## Abstention Threshold

Kairo abstains (asks the user instead of suggesting) when `calibrated_score < 60%`.
This is enforced in `memory::feedback::ConfidenceEngine::unified_confidence`.
