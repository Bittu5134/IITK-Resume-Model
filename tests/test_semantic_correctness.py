"""Hard negative and positive tests for semantic correctness.

These tests verify that the matcher correctly rejects invalid semantic mappings
and accepts valid ones based on actual evidence rather than section membership.
"""
from pathlib import Path

from resume_engine.evidence.extractor import EvidenceExtractor
from resume_engine.matching.matcher import HybridMatcher
from resume_engine.ontology.roles import load_role_graphs
from resume_engine.parser.pdf_parser import parse_pdf


GOLDEN = Path(__file__).parent / "fixtures" / "golden_resume_01.pdf"


class TestHardNegatives:
    """Tests that verify INCORRECT semantic mappings are rejected."""
    
    def test_business_revenue_not_mathematics(self):
        """Business revenue growth should NOT match mathematics competency."""
        ast = parse_pdf(GOLDEN)
        extractor = EvidenceExtractor()
        evidence = extractor.extract(ast)
        
        # Find the business revenue claim
        revenue_claims = [c for c in evidence.claims if "revenue growth" in c.text.lower()]
        assert len(revenue_claims) > 0, "Should have revenue growth claim"
        
        # Test against quant role
        roles = load_role_graphs()
        matcher = HybridMatcher()
        matches = matcher.match(evidence, roles["quant"])
        
        # Revenue claim should NOT match mathematics
        revenue_claim_id = revenue_claims[0].claim_id
        math_matches = [m for m in matches if m.competency == "mathematics" and m.claim_id == revenue_claim_id]
        assert len(math_matches) == 0, f"Revenue claim {revenue_claim_id} should not match mathematics"
    
    def test_mobilenet_research_not_probability(self):
        """MobileNet classifier research should NOT automatically match probability."""
        ast = parse_pdf(GOLDEN)
        extractor = EvidenceExtractor()
        evidence = extractor.extract(ast)
        
        # Find MobileNet claims
        mobilenet_claims = [c for c in evidence.claims if "mobilenet" in c.text.lower()]
        assert len(mobilenet_claims) > 0, "Should have MobileNet claim"
        
        roles = load_role_graphs()
        matcher = HybridMatcher()
        matches = matcher.match(evidence, roles["quant"])
        
        # MobileNet claim should NOT match probability without explicit probability keywords
        mobilenet_claim_id = mobilenet_claims[0].claim_id
        prob_matches = [m for m in matches if m.competency == "probability" and m.claim_id == mobilenet_claim_id]
        
        # Only allow if the claim actually contains probability keywords
        if len(prob_matches) > 0:
            claim_text = mobilenet_claims[0].text.lower()
            has_prob_keywords = any(word in claim_text for word in 
                                   ["probability", "probabilistic", "stochastic", "bayesian", "monte carlo"])
            assert has_prob_keywords, f"MobileNet claim should only match probability with explicit keywords, got: {claim_text}"
    
    def test_research_section_not_publication(self):
        """Being in Research section should NOT automatically mean publications."""
        ast = parse_pdf(GOLDEN)
        extractor = EvidenceExtractor()
        evidence = extractor.extract(ast)
        
        # Find Research section claims
        research_claims = [c for c in evidence.claims if c.section == "Research"]
        assert len(research_claims) > 0, "Should have Research claims"
        
        roles = load_role_graphs()
        matcher = HybridMatcher()
        matches = matcher.match(evidence, roles["core"])
        
        # Research claims should NOT automatically match publications
        pub_matches = [m for m in matches if m.competency == "publications"]
        for match in pub_matches:
            # Find the actual claim
            claim = next(c for c in evidence.claims if c.claim_id == match.claim_id)
            claim_text = claim.text.lower()
            has_pub_keywords = any(word in claim_text for word in 
                                  ["published", "publication", "paper", "journal", "conference", "doi"])
            assert has_pub_keywords, f"Publication match without keywords: {claim_text[:60]}..."
    
    def test_business_analyst_internship_not_core(self):
        """Business Analyst internship should NOT be strong for Core Engineering."""
        ast = parse_pdf(GOLDEN)
        extractor = EvidenceExtractor()
        evidence = extractor.extract(ast)
        
        # Find BA internship claims using entry context or business analysis evidence type
        ba_claims = [c for c in evidence.claims if c.section == "Experience" and 
                    (("business analyst" in c.entry_context.lower() or "navikra" in c.entry_context.lower()) or
                     ("business analyst" in c.text.lower() or "navikra" in c.text.lower()) or
                     any(str(et).endswith("business_analysis") for et in c.evidence_types))]
        assert len(ba_claims) > 0, "Should have Business Analyst claims"
        
        roles = load_role_graphs()
        matcher = HybridMatcher()
        matches = matcher.match(evidence, roles["core"])
        
        # BA claims should have low relevance for core internships
        ba_internship_matches = [m for m in matches if m.competency == "internships" and 
                                m.claim_id in [c.claim_id for c in ba_claims]]
        
        if len(ba_internship_matches) > 0:
            # Should have low scores for core relevance
            for match in ba_internship_matches:
                assert match.final_score < 0.6, f"BA internship too high for core: {match.final_score}"
    
    def test_hostel_leadership_not_sde_impact(self):
        """Hostel leadership metrics should NOT contribute to SDE technical impact."""
        ast = parse_pdf(GOLDEN)
        extractor = EvidenceExtractor()
        evidence = extractor.extract(ast)
        
        # Find hostel-related claims
        hostel_claims = [c for c in evidence.claims if 
                        any(word in c.text.lower() for word in ["hostel", "mess", "accommodation"])]
        assert len(hostel_claims) > 0, "Should have hostel claims"
        
        roles = load_role_graphs()
        matcher = HybridMatcher()
        matches = matcher.match(evidence, roles["sde"])
        
        # Hostel claims should NOT strongly match SDE impact
        hostel_impact_matches = [m for m in matches if m.competency == "impact" and 
                                m.claim_id in [c.claim_id for c in hostel_claims]]
        
        # Allow some matches but they should not be the PRIMARY source of SDE impact
        if len(hostel_impact_matches) > 0:
            for match in hostel_impact_matches:
                assert match.final_score < 0.7, f"Hostel claim too high for SDE impact: {match.final_score}"


class TestHardPositives:
    """Tests that verify CORRECT semantic mappings are accepted."""
    
    def test_sql_engineering_matches_sde(self):
        """SQL pipeline engineering should match SDE software_engineering."""
        ast = parse_pdf(GOLDEN)
        extractor = EvidenceExtractor()
        evidence = extractor.extract(ast)
        
        # Find SQL engineering claim
        sql_claims = [c for c in evidence.claims if "sql" in c.text.lower() and "engineered" in c.text.lower()]
        assert len(sql_claims) > 0, "Should have SQL engineering claim"
        
        roles = load_role_graphs()
        matcher = HybridMatcher()
        matches = matcher.match(evidence, roles["sde"])
        
        # Should match software_engineering
        sql_claim_id = sql_claims[0].claim_id
        eng_matches = [m for m in matches if m.competency == "software_engineering" and m.claim_id == sql_claim_id]
        assert len(eng_matches) > 0, "SQL engineering should match software_engineering"
        assert eng_matches[0].final_score > 0.3, f"SQL engineering score too low: {eng_matches[0].final_score}"
    
    def test_leadership_por_matches_consulting(self):
        """Leadership in PoR should strongly match consulting leadership."""
        ast = parse_pdf(GOLDEN)
        extractor = EvidenceExtractor()
        evidence = extractor.extract(ast)
        
        # Find leadership claims in PoR section
        por_leadership = [c for c in evidence.claims if c.section == "Positions of Responsibility" and
                         any(word in c.text.lower() for word in ["elected", "convener", "oversaw"])]
        assert len(por_leadership) > 0, "Should have PoR leadership claims"
        
        roles = load_role_graphs()
        matcher = HybridMatcher()
        matches = matcher.match(evidence, roles["consulting"])
        
        # Should strongly match leadership
        por_claim_id = por_leadership[0].claim_id
        leadership_matches = [m for m in matches if m.competency == "leadership" and m.claim_id == por_claim_id]
        assert len(leadership_matches) > 0, "PoR leadership should match consulting leadership"
        assert leadership_matches[0].final_score > 0.4, f"PoR leadership score too low: {leadership_matches[0].final_score}"
    
    def test_tensorflow_scikit_matches_ml_engineering(self):
        """TensorFlow and scikit-learn usage should match ML engineering."""
        ast = parse_pdf(GOLDEN)
        extractor = EvidenceExtractor()
        evidence = extractor.extract(ast)
        
        # Find ML framework claims
        ml_claims = [c for c in evidence.claims if 
                    any(fw in c.text.lower() for fw in ["tensorflow", "scikit", "sklearn"])]
        assert len(ml_claims) > 0, "Should have ML framework claims"
        
        # Verify they have ML engineering evidence type
        ml_claim = ml_claims[0]
        from resume_engine.parser.models import EvidenceType
        assert EvidenceType.ML_ENGINEERING in ml_claim.evidence_types, "Should have ML engineering evidence type"
        
        roles = load_role_graphs()
        matcher = HybridMatcher()
        
        # For core role, should match technical_depth or research
        core_matches = matcher.match(evidence, roles["core"])
        ml_claim_id = ml_claim.claim_id
        relevant_core_matches = [m for m in core_matches if 
                                m.competency in ["technical_depth", "research"] and 
                                m.claim_id == ml_claim_id and m.final_score > 0.3]
        assert len(relevant_core_matches) > 0, f"ML frameworks should match core technical competencies, found matches: {[(m.competency, m.final_score) for m in core_matches if m.claim_id == ml_claim_id]}"