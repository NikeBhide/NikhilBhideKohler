"""
Extraction Agent - Theme Inference Module
Maps product descriptions to Kohler's 25 official design themes
"""

import json
import re
from typing import List, Dict, Tuple
from collections import Counter


class ExtractionAgent:
    """
    Infers design themes from product descriptions using keyword matching and logical inference.
    """

    def __init__(self):
        """Initialize with Kohler's 25 official themes and keywords."""
        self.themes = {
            "Modern": {
                "keywords": ["crisp", "clean", "contemporary", "sleek", "minimalist",
                            "angular", "geometric", "linear", "modern", "streamlined"],
                "inference_patterns": [r"crisp\s+lines", r"clean\s+aesthetic", r"contemporary\s+design"]
            },
            "Classic": {
                "keywords": ["traditional", "timeless", "elegant", "refined", "heritage",
                            "formal", "classic", "ornate", "detailed"],
                "inference_patterns": [r"classic.*style", r"traditional.*design", r"heritage\s+collection"]
            },
            "Spa": {
                "keywords": ["wellness", "relaxation", "therapeutic", "hydrotherapy", "steam",
                            "massage", "heated", "blissful", "soothing", "invigorating"],
                "inference_patterns": [r"whirlpool\s+jets?", r"bubble.*massage", r"heated\s+surface", r"airjets"]
            },
            "Luxury": {
                "keywords": ["premium", "high-end", "bespoke", "artisanal", "crafted",
                            "signature", "luxury", "sophisticated"],
                "inference_patterns": [r"premium\s+collection", r"luxury\s+experience", r"signature\s+collection"]
            },
            "Minimalist": {
                "keywords": ["simple", "essential", "uncluttered", "functional", "pared-down",
                            "minimal", "essence", "purposeful"],
                "inference_patterns": [r"pursuit\s+of\s+simplicity", r"unadorned", r"essence"]
            },
            "Transitional": {
                "keywords": ["blend", "fusion", "versatile", "adaptable", "bridge", "balanced"],
                "inference_patterns": [r"blend.*traditional", r"versatile.*design"]
            },
            "Industrial": {
                "keywords": ["raw", "metal", "concrete", "warehouse", "exposed", "urban", "industrial"],
                "inference_patterns": [r"industrial\s+chic", r"exposed.*finish"]
            },
            "Coastal": {
                "keywords": ["nautical", "beach", "bright", "fresh", "maritime", "breezy", "coastal"],
                "inference_patterns": [r"coastal\s+design", r"beach.*inspired"]
            },
            "Rustic": {
                "keywords": ["natural", "wood", "stone", "earthy", "reclaimed", "weathered", "rustic"],
                "inference_patterns": [r"natural\s+materials", r"rustic.*style"]
            },
            "Scandinavian": {
                "keywords": ["nordic", "scandinavian", "functional", "light", "minimalist", "beauty"],
                "inference_patterns": [r"scandinavian\s+design", r"nordic.*style"]
            },
            "Art Deco": {
                "keywords": ["geometric", "bold", "glamorous", "deco", "vintage", "elegance"],
                "inference_patterns": [r"art\s+deco", r"deco.*style"]
            },
            "Victorian": {
                "keywords": ["ornate", "detailed", "classical", "gothic", "period", "ornamental"],
                "inference_patterns": [r"victorian.*style", r"ornate.*design", r"ball-and-claw"]
            },
            "Mediterranean": {
                "keywords": ["warm", "tuscan", "italian", "spanish", "earthy", "mediterranean"],
                "inference_patterns": [r"mediterranean\s+style", r"tuscan.*design"]
            },
            "Japanese": {
                "keywords": ["zen", "harmony", "natural", "minimalist", "japanese", "organic"],
                "inference_patterns": [r"japanese.*design", r"zen\s+harmony"]
            },
            "Contemporary": {
                "keywords": ["current", "cutting-edge", "innovation", "contemporary", "modern"],
                "inference_patterns": [r"contemporary\s+design", r"cutting-edge"]
            },
            "Transitional Modern": {
                "keywords": ["modern", "traditional", "balance", "versatile"],
                "inference_patterns": [r"transitional.*modern"]
            },
            "Eclectic": {
                "keywords": ["mix", "curated", "unique", "personalized", "eclectic"],
                "inference_patterns": [r"eclectic\s+design"]
            },
            "Bohemian": {
                "keywords": ["artistic", "free-spirited", "layered", "unconventional", "bohemian"],
                "inference_patterns": [r"bohemian\s+style"]
            },
            "Glam": {
                "keywords": ["glamorous", "shiny", "bold", "statement", "luxe", "polish"],
                "inference_patterns": [r"glam.*style", r"glamorous.*design"]
            },
            "Industrial Chic": {
                "keywords": ["industrial", "modern", "practical", "raw", "chic"],
                "inference_patterns": [r"industrial\s+chic"]
            },
            "Farmhouse": {
                "keywords": ["rustic", "farmhouse", "country", "lived-in", "farmhouse"],
                "inference_patterns": [r"farmhouse\s+style"]
            },
            "Mid-Century": {
                "keywords": ["mid-century", "retro", "vintage", "atomic", "mid-century modern"],
                "inference_patterns": [r"mid-century\s+modern", r"retro.*design"]
            },
            "Transitional Spa": {
                "keywords": ["spa", "traditional", "blend", "therapeutic", "wellness"],
                "inference_patterns": [r"spa.*transitional"]
            },
            "Urban": {
                "keywords": ["city", "urban", "loft", "metropolitan", "modern"],
                "inference_patterns": [r"urban\s+loft", r"metropolitan\s+design"]
            },
            "Nature-Inspired": {
                "keywords": ["organic", "biophilic", "natural", "forms", "sustainable", "nature"],
                "inference_patterns": [r"nature-inspired", r"organic\s+shape", r"biophilic"]
            }
        }

    def _preprocess_text(self, text: str) -> str:
        """Convert text to lowercase and clean up whitespace."""
        return " ".join(text.lower().split())

    def _count_keyword_matches(self, text: str, keywords: List[str]) -> int:
        """Count how many theme keywords appear in the text."""
        text = self._preprocess_text(text)
        count = 0
        for keyword in keywords:
            # Use word boundaries to match whole words only
            pattern = r"\b" + re.escape(keyword) + r"\b"
            matches = len(re.findall(pattern, text))
            count += matches
        return count

    def _apply_inference_patterns(self, text: str, patterns: List[str]) -> float:
        """
        Apply logical inference patterns to detect theme.
        Returns a score (0.0-1.0) based on pattern matches.
        """
        text = self._preprocess_text(text)
        if not patterns:
            return 0.0

        matches = 0
        for pattern in patterns:
            if re.search(pattern, text):
                matches += 1

        # Normalize to 0-1 range
        return min(1.0, matches / len(patterns))

    # A safe, broadly-compatible default for the rare case where a user's
    # free-text description shares literally zero keywords with any of the
    # 25 themes -- used only by guarantee_result, and only as a last resort
    # (see infer_themes below).
    FALLBACK_THEME = "Transitional"

    def infer_themes(self, product: Dict, min_confidence: float = 0.2, guarantee_result: bool = False) -> Dict:
        """
        Infer design themes from product description and name.

        Args:
            product: Dict with 'name' and 'description' keys
            min_confidence: confidence threshold a theme must clear to be
                considered a real match (used for product catalog tagging).
            guarantee_result: when True (used for a user's own free-text
                vision description, not catalog products), never return an
                empty list just because nothing cleared min_confidence --
                fall back to the best-scoring theme(s) found, honestly
                reported at whatever confidence they actually earned, and
                only fall back further to FALLBACK_THEME if literally no
                keyword anywhere matched at all. The caller is expected to
                still let the person override the guess; this only avoids
                the dead end of "couldn't match anything, pick for yourself"
                that throws away a real (if imperfect) reading of the text.

        Returns:
            Dict with 'inferred_themes' list (sorted by confidence),
            'primary_theme', and 'low_confidence' (True when the result
            came from the guarantee_result fallback rather than a real
            match above min_confidence).
        """
        # Combine name and description for keyword matching
        combined_text = f"{product.get('name', '')} {product.get('description', '')}"

        if not combined_text.strip():
            if guarantee_result:
                return {
                    "inferred_themes": [{"theme": self.FALLBACK_THEME, "confidence": 0.0, "keywords": []}],
                    "primary_theme": self.FALLBACK_THEME,
                    "low_confidence": True,
                }
            return {"inferred_themes": [], "primary_theme": None, "low_confidence": False}

        theme_scores = {}

        # Score each theme
        for theme_name, theme_data in self.themes.items():
            # Count keyword matches
            keyword_matches = self._count_keyword_matches(
                combined_text,
                theme_data["keywords"]
            )

            # Apply inference patterns
            inference_score = self._apply_inference_patterns(
                combined_text,
                theme_data["inference_patterns"]
            )

            # Combined confidence score
            # Keyword matching: 70% weight, Inference patterns: 30% weight
            if keyword_matches > 0 or inference_score > 0:
                confidence = (keyword_matches * 0.7 / max(len(theme_data["keywords"]), 1)) + (inference_score * 0.3)
                # Normalize to 0-1 range
                confidence = min(1.0, confidence)
                theme_scores[theme_name] = confidence

        def _entry(theme, score):
            return {
                "theme": theme,
                "confidence": round(score, 2),
                "keywords": [k for k in self.themes[theme]["keywords"]
                            if re.search(r"\b" + re.escape(k) + r"\b", combined_text.lower())]
            }

        # Filter themes clearing min_confidence and sort by confidence
        inferred_themes = [
            _entry(theme, score)
            for theme, score in theme_scores.items()
            if score > min_confidence
        ]
        inferred_themes.sort(key=lambda x: x["confidence"], reverse=True)
        inferred_themes = inferred_themes[:4]

        low_confidence = False
        if not inferred_themes and guarantee_result:
            low_confidence = True
            if theme_scores:
                # Nothing cleared the bar, but something scored above zero
                # -- that's still a real (if weak) signal, worth surfacing
                # as a best guess rather than reporting no match at all.
                ranked = sorted(theme_scores.items(), key=lambda kv: kv[1], reverse=True)
                inferred_themes = [_entry(theme, score) for theme, score in ranked[:2]]
            else:
                # Literally no keyword anywhere matched -- fall back to a
                # single safe, broadly-compatible default rather than
                # leaving the person with nothing to react to.
                inferred_themes = [{"theme": self.FALLBACK_THEME, "confidence": 0.0, "keywords": []}]

        return {
            "inferred_themes": inferred_themes,
            "primary_theme": inferred_themes[0]["theme"] if inferred_themes else None,
            "low_confidence": low_confidence,
        }

    def process_products(self, products: List[Dict]) -> List[Dict]:
        """
        Process a list of products and add inferred themes to each.

        Args:
            products: List of product dicts with 'name' and 'description'

        Returns:
            List of products with added 'inferred_themes' and 'primary_theme'
        """
        processed = []
        for product in products:
            enriched = product.copy()
            theme_data = self.infer_themes(product)
            enriched.update(theme_data)
            processed.append(enriched)

        return processed


def main():
    """Test the Extraction Agent with sample products."""
    agent = ExtractionAgent()

    # Sample product data (from scraper output)
    sample_products = [
        {
            "sku": "K-26107-LA-0",
            "name": "Entity 60\" x 36\" Alcove Bath",
            "category": "Bathtubs",
            "price": 818.25,
            "description": "Defined by crisp lines and a clean, simple aesthetic, the KOHLER Entity bath complements a wide range of design languages. A comfortable sloped backrest provides support as you soak and unwind. The low step-over height makes this 60\" x 36\" rectangular alcove bath easy to access and ideal for bathing."
        },
        {
            "sku": "K-1125-LA-0",
            "name": "Archer 72\" x 36\" Alcove Bath",
            "category": "Bathtubs",
            "price": 1510.69,
            "description": "Taking its design cues from traditional Craftsman furniture, the KOHLER Archer line of baths reveals beveled edges and curved bases for a clean, sophisticated style. This 72\" x 36\" rectangular alcove bath offers a low step-over height while allowing for deep, comfortable soaking."
        },
        {
            "sku": "K-1967-GH-0",
            "name": "Sunstruck 65.5\" x 35.5\" Freestanding Heated BubbleMassage Air Bath",
            "category": "Bathtubs",
            "price": 5141.66,
            "description": "Completely surround your body in a soothing cushion of heated massaging bubbles in this KOHLER Sunstruck freestanding air bath. With airjets pushing humidified air through the water, this bath delivers a blissfully warm, invigorating full-body massage experience."
        },
        {
            "sku": "K-21388-0",
            "name": "Brazn 66\" x 35\" Freestanding Bath",
            "category": "Bathtubs",
            "price": 7629.71,
            "description": "Every shape is a statement. The KOHLER Brazn collection is unadorned and refined to an essence. This 66\" x 35\" oval freestanding bath proclaims itself the relentless pursuit of simplicity. Purposeful in every detail. Bold in any space."
        },
        {
            "sku": "K-710-W-0",
            "name": "Iron Works Historic 66\" x 36\" Freestanding Bath",
            "category": "Bathtubs",
            "price": 4357.57,
            "description": "This freestanding cast iron bath features ornate ball-and-claw feet for an antique-inspired look, enhanced by the modern comforts of built-in back support and a Safeguard slip-resistant surface."
        }
    ]

    # Process products
    enriched_products = agent.process_products(sample_products)

    # Display results
    print("=" * 80)
    print("EXTRACTION AGENT - THEME INFERENCE RESULTS")
    print("=" * 80)

    for product in enriched_products:
        print(f"\nProduct: {product['name']}")
        print(f"SKU: {product['sku']}")
        print(f"Primary Theme: {product['primary_theme']}")
        print(f"Inferred Themes:")
        for theme in product['inferred_themes']:
            print(f"  - {theme['theme']}: {theme['confidence']} confidence")
            print(f"    Keywords matched: {', '.join(theme['keywords'][:3])}")


if __name__ == "__main__":
    main()
