// phantom-core/tests/test_domain_degradation.rs

use phantom_core::swarm::SwarmOrchestrator;
use phantom_core::plugin::DomainCapability;

#[test]
fn test_orchestrator_domain_capabilities() {
    let orchestrator = SwarmOrchestrator::new_for_test();
    
    // Check that "legal" capability is Real
    let legal_cap = orchestrator.get_domain_capability("legal");
    assert_eq!(legal_cap, Some(DomainCapability::Real));

    // Check that prompt-only domains like "medical" or "sales" are PromptOnly
    let medical_cap = orchestrator.get_domain_capability("medical");
    assert_eq!(medical_cap, Some(DomainCapability::PromptOnly));

    let sales_cap = orchestrator.get_domain_capability("sales");
    assert_eq!(sales_cap, Some(DomainCapability::PromptOnly));

    let engineer_cap = orchestrator.get_domain_capability("engineer");
    assert_eq!(engineer_cap, Some(DomainCapability::PromptOnly));
}

#[tokio::test]
async fn test_pro_stubs_fail() {
    use phantom_core::pro::{KairoPro, TeamMemoryVault, AuditExport};
    let pro = KairoPro::new();
    let res = TeamMemoryVault::sync_to_s3(&pro).await;
    assert!(res.is_err());
    assert_eq!(res.unwrap_err().to_string(), "Pro sync not yet available");
    
    let res2 = AuditExport::export_csv(&pro, "user", "app", "agent", "hash", "outcome", 100);
    assert!(res2.is_err());
    assert_eq!(res2.unwrap_err().to_string(), "Audit export not yet available");
}
