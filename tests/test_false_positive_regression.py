"""
Regression tests for semantic false positives.
These tests ensure the system correctly rejects invalid evidence patterns
that could occur across diverse IITK resumes.
"""
import pytest
from resume_engine.parser.pdf_parser import parse_pdf
from resume_engine.evidence.extractor import EvidenceExtractor
from resume_engine.ontology.roles import load_role_graphs
from resume_engine.matching.matcher import HybridMatcher
from resume_engine.parser.models import EvidenceType


class TestFalsePositiveRegression:
    """Tests to prevent false positive matches that could affect IITK students."""

    def test_cohort_analysis_not_rigorous_mathematics(self):
        """'Formulated cohort analysis models' should NOT create strong mathematics evidence."""
        # Create a mock claim with cohort analysis
        extractor = EvidenceExtractor()
        
        # Test the classification directly
        evidence_types, project_types, impact_types = extractor._classify_evidence_types(
            "Formulated cohort analysis models to track retention patterns",
            [], [], "Experience", [], []
        )
        
        # Should have business_analysis but NOT mathematical (due to veto)
        assert EvidenceType.BUSINESS_ANALYSIS in evidence_types
        assert EvidenceType.MATHEMATICAL not in evidence_types, "Cohort analysis should not trigger mathematical evidence"

    def test_guided_ml_students_not_strong_statistics(self):
        """'Guided students in ML & Fintech' should NOT create strong statistics evidence."""
        extractor = EvidenceExtractor()
        
        evidence_types, _, _ = extractor._classify_evidence_types(
            "Guided 25 students in ML & Fintech leading a summer project",
            ["machine_learning", "fintech"], [], "Extracurricular", [], []
        )
        
        # Should not have strong statistical evidence from mentorship alone
        assert EvidenceType.STATISTICAL not in evidence_types, "ML mentorship should not create statistics evidence"

    def test_business_analyst_not_core_engineering(self):
        """Business Analyst internship should have minimal core engineering relevance."""
        extractor = EvidenceExtractor()
        
        evidence_types, _, _ = extractor._classify_evidence_types(
            "Business Analyst Intern - Optimized pricing strategies for B2B clients",
            ["business_optimization"], [], "Experience", [], []
        )
        
        domain_relevance = extractor._compute_domain_relevance(
            evidence_types, [], [], "Experience"
        )
        
        # Should have very low core relevance
        assert domain_relevance["core"] < 0.3, f"Business analyst should have low core relevance, got {domain_relevance['core']}"
        assert domain_relevance["consulting"] > 0.8, "Business analyst should have high consulting relevance"

    def test_revenue_growth_not_sde_technical_impact(self):
        """'Delivered 20% revenue growth' should NOT contribute to SDE technical impact."""
        extractor = EvidenceExtractor()
        
        # Business revenue metrics should not be technical impact for SDE
        evidence_types, _, impact_types = extractor._classify_evidence_types(
            "Delivered 20% revenue growth through pricing optimization strategies",
            ["business_optimization"], [], "Experience", [], [{"kind": "percentage", "is_impact_relevant": True}]
        )
        
        domain_relevance = extractor._compute_domain_relevance(
            evidence_types, [], impact_types, "Experience"
        )
        
        # Should have low SDE relevance due to business context penalty
        assert domain_relevance["sde"] < 0.4, f"Revenue growth should not boost SDE scores, got {domain_relevance['sde']}"

    def test_pricing_optimization_not_programming(self):
        """'Pricing optimization' alone should NOT be programming evidence."""
        extractor = EvidenceExtractor()
        
        evidence_types, _, _ = extractor._classify_evidence_types(
            "Developed pricing optimization strategies across multiple platforms",
            [], [], "Experience", [], []
        )
        
        # Should not trigger programming evidence without explicit tech
        assert EvidenceType.PROGRAMMING not in evidence_types, "Pricing optimization should not be programming"
        assert EvidenceType.BUSINESS_ANALYSIS in evidence_types, "Should be classified as business analysis"

    def test_ml_classifier_not_quant_finance(self):
        """'ML classifier' should NOT be quantitative finance project."""
        extractor = EvidenceExtractor()
        
        evidence_types, project_types, _ = extractor._classify_evidence_types(
            "Built ML classifier for image recognition using TensorFlow",
            ["tensorflow", "machine_learning"], [], "Projects", [], []
        )
        
        domain_relevance = extractor._compute_domain_relevance(
            evidence_types, project_types, [], "Projects"
        )
        
        # Should not have high quant relevance (some is OK due to ML)
        assert domain_relevance["quant"] < 0.6, "Generic ML project should not be strongly quant-relevant"

    def test_research_section_not_automatic_publication(self):
        """Being in Research section should NOT automatically imply publication."""
        extractor = EvidenceExtractor()
        
        evidence_types, _, _ = extractor._classify_evidence_types(
            "Investigated novel approaches for fog detection in computer vision",
            [], [], "Research", [], []
        )
        
        # Should have research evidence but NOT publication
        assert EvidenceType.RESEARCH in evidence_types
        assert EvidenceType.PUBLICATION not in evidence_types, "Research work should not automatically imply publication"

    def test_github_profile_not_open_source_contribution(self):
        """Having 'GitHub profile' should NOT imply open source contribution."""
        extractor = EvidenceExtractor()
        
        evidence_types, _, _ = extractor._classify_evidence_types(
            "GitHub profile available at github.com/username",
            [], [], "Header", [], []
        )
        
        # Should not trigger open source evidence from profile link alone
        assert EvidenceType.OPEN_SOURCE not in evidence_types, "GitHub profile should not imply open source contribution"

    def test_business_model_not_mathematics(self):
        """'Business model' should NOT trigger mathematical evidence."""
        extractor = EvidenceExtractor()
        
        evidence_types, _, _ = extractor._classify_evidence_types(
            "Designed business model for sustainable startup growth",
            [], [], "Projects", [], []
        )
        
        assert EvidenceType.MATHEMATICAL not in evidence_types, "Business model should not trigger mathematics"
        assert EvidenceType.BUSINESS_ANALYSIS in evidence_types, "Should be business analysis"

    def test_inter_iit_event_mentions_not_false_triggers(self):
        """Mentions of Inter IIT events should not create false competency matches."""
        extractor = EvidenceExtractor()
        
        # Test IITK entity normalization
        normalized = extractor._normalize_iitk_entity("Inter IIT Tech Meet 14.0")
        assert "Inter IIT" in normalized, "Should normalize Inter IIT correctly"
        
        # Should not create random competency boosts
        evidence_types, _, _ = extractor._classify_evidence_types(
            "Participated in Inter IIT Tech Meet representing our institute",
            [], [], "Extracurricular", [], []
        )
        
        # Participation alone should not imply specific technical evidence
        technical_types = [EvidenceType.PROGRAMMING, EvidenceType.SOFTWARE_ENGINEERING, EvidenceType.COMPETITIVE_PROGRAMMING]
        assert not any(et in evidence_types for et in technical_types), "Participation should not imply specific technical skills"