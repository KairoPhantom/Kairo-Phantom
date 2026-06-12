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
