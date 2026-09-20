"""
Recommendation Agent - Bundle Recommendation & Refinement
Scores products and recommends cohesive bathroom bundles
"""

from typing import List, Dict, Set, Tuple
from collections import defaultdict
import json


class RecommendationAgent:
    """
    Recommends KOHLER product bundles based on user constraints and scoring.
    Handles iterative refinement when users lock/unlock products.
    """

    def __init__(self):
        """Initialize scoring weights and constraint rules."""
        # Scoring weights
        self.THEME_MATCH_WEIGHT = 0.35
        self.BUNDLE_COHESION_WEIGHT = 0.50
        self.CATEGORY_BALANCE_WEIGHT = 0.15

        # Bundle cohesion sub-weights
        self.COHESION_PRIMARY_THEME = 0.4
        self.COHESION_COLOR = 0.3
        self.COHESION_PRICE_TIER = 0.2
        self.COHESION_VISUAL_STYLE = 0.1

        # Fixed, deterministic order to process requested categories in.
        # Using a plain set's iteration order here is what caused the same
        # inputs to produce different bundles across requests (a set's
        # order depends on the interpreter's hash seed, which can change
        # between process restarts) -- this list makes the fill order,
        # and therefore the result, reproducible.
        self.CATEGORY_PRIORITY_ORDER = [
            "Bathtubs", "Showers", "Toilets", "Toilet Bidet Seats",
            "Vanities", "Basins", "Faucets", "Mirrors", "Cabinets",
            "Digital Showering", "Lighting", "Bathroom Accessories",
        ]

    def _ordered_categories(self, categories) -> List[str]:
        """Sort requested categories into a fixed, deterministic order."""
        order = {c: i for i, c in enumerate(self.CATEGORY_PRIORITY_ORDER)}
        fallback = len(self.CATEGORY_PRIORITY_ORDER)
        return sorted(categories, key=lambda c: (order.get(c, fallback), c))

    def validate_hard_constraints(
        self,
        product: Dict,
        user_budget: float,
        user_categories: Set[str],
        in_stock_only: bool = True
    ) -> bool:
        """
        Check hard constraints (filters).

        Args:
            product: Product dict with price, category, availability
            user_budget: Max budget (single product must fit)
            user_categories: Set of allowed categories
            in_stock_only: If True, only include in-stock items

        Returns:
            True if product passes all hard constraints
        """
        # Price constraint
        if product.get("price", 0) > user_budget:
            return False

        # Category constraint
        if product.get("category") not in user_categories:
            return False

        # Availability constraint
        if in_stock_only and not product.get("availability", True):
            return False

        return True

    def calculate_theme_match(
        self,
        product_themes: List[Dict],
        user_themes: List[str]
    ) -> float:
        """
        Calculate how well product themes match user's selected themes.

        Args:
            product_themes: List of {"theme": ..., "confidence": ...} from product
            user_themes: User's selected themes (list of theme names)

        Returns:
            Score 0-1.0 representing theme match quality
        """
        if not product_themes or not user_themes:
            return 0.0

        product_theme_names = [t["theme"] for t in product_themes]

        # Calculate overlap
        overlap = set(product_theme_names) & set(user_themes)

        if not overlap:
            return 0.0

        # Get average confidence of overlapping themes
        overlapping_confidences = [
            t["confidence"] for t in product_themes
            if t["theme"] in overlap
        ]

        # Score based on overlap percentage + confidence
        overlap_ratio = len(overlap) / len(user_themes)
        avg_confidence = sum(overlapping_confidences) / len(overlapping_confidences)

        # Combined score (40% overlap, 60% confidence)
        score = (overlap_ratio * 0.4) + (avg_confidence * 0.6)

        return min(1.0, score)

    def categorize_price_tier(self, price: float) -> str:
        """
        Categorize product price into tier.

        Args:
            price: Product price

        Returns:
            Tier name: "budget", "mid-range", "premium", "luxury"
        """
        if price < 50000:
            return "budget"
        elif price < 200000:
            return "mid-range"
        elif price < 500000:
            return "premium"
        else:
            return "luxury"

    def calculate_bundle_cohesion(
        self,
        candidate_product: Dict,
        locked_products: List[Dict]
    ) -> float:
        """
        Calculate how well candidate product fits with already-selected products.

        Args:
            candidate_product: Product being evaluated
            locked_products: Already-selected/locked products

        Returns:
            Score 0-1.0 representing bundle cohesion
        """
        if not locked_products:
            return 0.5  # Neutral score if no locked products

        cohesion_score = 0.0

        # 1. Primary theme alignment (0.4 weight)
        candidate_primary = candidate_product.get("primary_theme")
        locked_primaries = [p.get("primary_theme") for p in locked_products]

        if candidate_primary and candidate_primary in locked_primaries:
            theme_cohesion = 1.0
        else:
            # Check for theme keyword overlap
            candidate_themes = {t["theme"] for t in candidate_product.get("inferred_themes", [])}
            locked_themes = set()
            for p in locked_products:
                for t in p.get("inferred_themes", []):
                    locked_themes.add(t["theme"])

            theme_overlap = len(candidate_themes & locked_themes) / max(len(candidate_themes | locked_themes), 1)
            theme_cohesion = theme_overlap

        cohesion_score += theme_cohesion * self.COHESION_PRIMARY_THEME

        # 2. Color/finish consistency (0.3 weight)
        candidate_color = candidate_product.get("color_finish", "")
        locked_colors = [p.get("color_finish", "") for p in locked_products]

        # Simple color match (exact match or partial match)
        color_matches = sum(
            1 for color in locked_colors
            if color and color.lower() in candidate_color.lower() or candidate_color.lower() in color.lower()
        )
        color_cohesion = color_matches / len(locked_colors) if locked_colors else 0.5
        cohesion_score += color_cohesion * self.COHESION_COLOR

        # 3. Price tier consistency (0.2 weight)
        candidate_tier = self.categorize_price_tier(candidate_product.get("price", 0))
        locked_tiers = [self.categorize_price_tier(p.get("price", 0)) for p in locked_products]

        tier_matches = sum(1 for tier in locked_tiers if tier == candidate_tier)
        tier_cohesion = tier_matches / len(locked_tiers) if locked_tiers else 0.5
        cohesion_score += tier_cohesion * self.COHESION_PRICE_TIER

        # 4. Visual style consistency (0.1 weight) - based on primary theme
        # Themes with similar visual language
        style_groups = {
            "Modern": ["Modern", "Contemporary", "Minimalist", "Industrial"],
            "Classic": ["Classic", "Victorian", "Transitional", "Transitional Modern"],
            "Spa": ["Spa", "Transitional Spa", "Nature-Inspired"],
            "Luxury": ["Luxury", "Glam", "Art Deco"],
        }

        candidate_styles = []
        for group, themes in style_groups.items():
            if candidate_primary in themes:
                candidate_styles = themes
                break

        if candidate_styles:
            locked_style_matches = sum(
                1 for p in locked_products
                if p.get("primary_theme") in candidate_styles
            )
            style_cohesion = locked_style_matches / len(locked_products) if locked_products else 0.5
        else:
            style_cohesion = 0.5

        cohesion_score += style_cohesion * self.COHESION_VISUAL_STYLE

        return min(1.0, cohesion_score)

    def score_product(
        self,
        product: Dict,
        user_themes: List[str],
        locked_products: List[Dict],
        filled_categories: Set[str]
    ) -> float:
        """
        Calculate product score for recommendation.

        Scoring formula:
        SCORE = (Theme_Match × 0.35) + (Bundle_Cohesion × 0.50) + (Category_Balance × 0.15)

        Args:
            product: Product being scored
            user_themes: User's selected themes
            locked_products: Already-selected products
            filled_categories: Categories already filled

        Returns:
            Combined score 0-1.0
        """
        score = 0.0

        # 1. Theme Match (0.35 weight)
        theme_match = self.calculate_theme_match(
            product.get("inferred_themes", []),
            user_themes
        )
        score += theme_match * self.THEME_MATCH_WEIGHT

        # 2. Bundle Cohesion (0.50 weight)
        bundle_cohesion = self.calculate_bundle_cohesion(product, locked_products)
        score += bundle_cohesion * self.BUNDLE_COHESION_WEIGHT

        # 3. Category Balance (0.15 weight)
        # Penalty if category already filled
        product_category = product.get("category")
        if product_category in filled_categories:
            category_balance = 0.0
        else:
            category_balance = 1.0
        score += category_balance * self.CATEGORY_BALANCE_WEIGHT

        return min(1.0, score)

    def recommend_bundle(
        self,
        products: List[Dict],
        user_themes: List[str],
        user_budget: float,
        user_categories: Set[str],
        locked_products: List[Dict] = None
    ) -> Dict:
        """
        Recommend a complete bathroom bundle.

        Args:
            products: Full product catalog
            user_themes: User's selected theme preferences
            user_budget: Total budget for entire bundle
            user_categories: Categories user wants to include
            locked_products: Products user has locked (won't be replaced)

        Returns:
            Dict with recommended_bundle, total_price, alternatives
        """
        locked_products = locked_products or []

        # Track which categories have been filled
        filled_categories = {p.get("category") for p in locked_products}

        # Track total price
        current_total = sum(p.get("price", 0) for p in locked_products)

        # Remaining budget
        remaining_budget = user_budget - current_total

        # Find best product for each unfilled category, in a fixed order,
        # with a budget "reservation" so filling one category can never
        # eat the money another requested category needs.
        recommended = locked_products.copy()
        alternatives = defaultdict(list)
        unfilled_details = {}

        ordered_categories = self._ordered_categories(
            c for c in user_categories if c not in filled_categories
        )

        # Cheapest currently-available price per requested category
        # (computed once; the catalog doesn't change during this call).
        cheapest_by_category = {}
        for category in ordered_categories:
            available = [
                p for p in products
                if p.get("category") == category and p.get("availability", True)
            ]
            if available:
                cheapest_by_category[category] = min(p.get("price", 0) for p in available)

        # Decide, up front and in priority order, which categories can be
        # guaranteed a slot within the budget. Walking the list once and
        # greedily reserving each category's cheapest price (in priority
        # order) means: if the whole budget can't cover every requested
        # category, the drop is a deliberate, reproducible prioritization
        # decision -- not an accident of iteration order.
        guaranteed_categories = []
        budget_for_guarantees = remaining_budget
        for category in ordered_categories:
            cheapest = cheapest_by_category.get(category)
            if cheapest is not None and cheapest <= budget_for_guarantees:
                guaranteed_categories.append(category)
                budget_for_guarantees -= cheapest

        guaranteed_set = set(guaranteed_categories)

        for category in ordered_categories:
            if category not in guaranteed_set:
                # Diagnose WHY this category couldn't be filled, so the
                # frontend can explain it to the user instead of silently
                # dropping it.
                in_catalog = [p for p in products if p.get("category") == category]
                available = [p for p in in_catalog if p.get("availability", True)]

                if not in_catalog:
                    unfilled_details[category] = {
                        "reason": "not_in_catalog",
                        "cheapest_price": None,
                        "shortfall": None,
                    }
                elif not available:
                    unfilled_details[category] = {
                        "reason": "unavailable",
                        "cheapest_price": None,
                        "shortfall": None,
                    }
                else:
                    cheapest_price = min(p.get("price", 0) for p in available)
                    shortfall = max(0, cheapest_price - remaining_budget)
                    unfilled_details[category] = {
                        "reason": "budget",
                        "cheapest_price": cheapest_price,
                        "shortfall": shortfall,
                    }
                continue  # No available products in this category

            # Reserve the cheapest price of every OTHER still-unfilled
            # guaranteed category, so the pick for THIS category can never
            # spend money another guaranteed category needs.
            reserve = sum(
                cheapest_by_category[other]
                for other in guaranteed_categories
                if other != category and other not in filled_categories
            )
            budget_ceiling = max(0, remaining_budget - reserve)

            # Find all products in this category within the fair ceiling
            category_products = [
                p for p in products
                if self.validate_hard_constraints(
                    p,
                    budget_ceiling,
                    {category}
                )
            ]

            if not category_products:
                # Shouldn't happen given the guarantee above, but stay safe.
                continue

            # Score each product in category
            scored_products = [
                {
                    **p,
                    "score": self.score_product(
                        p,
                        user_themes,
                        recommended,
                        filled_categories
                    )
                }
                for p in category_products
            ]

            # Sort by score, tie-broken by SKU for full determinism
            scored_products.sort(key=lambda x: (-x["score"], x.get("sku", "")))

            # Recommend the top-scored product
            best = scored_products[0]
            recommended.append(best)
            filled_categories.add(category)
            remaining_budget -= best.get("price", 0)

            # Store alternatives (top 3)
            alternatives[category] = scored_products[:3]

        # Calculate total price
        total_price = sum(p.get("price", 0) for p in recommended)
        within_budget = total_price <= user_budget

        return {
            "recommended_bundle": recommended,
            "total_price": total_price,
            "within_budget": within_budget,
            "alternatives": dict(alternatives),
            "filled_categories": list(filled_categories),
            "unfilled_categories": list(set(user_categories) - filled_categories),
            "unfilled_details": unfilled_details,
            "remaining_budget": remaining_budget,
        }

    def refresh_bundle(
        self,
        products: List[Dict],
        user_themes: List[str],
        user_budget: float,
        user_categories: Set[str],
        locked_products: List[Dict],
        exclude_categories: Set[str] = None
    ) -> Dict:
        """
        Refresh bundle for unlocked categories while maintaining locked products.

        Args:
            products: Full product catalog
            user_themes: User's selected themes
            user_budget: Total budget
            user_categories: Categories user wants
            locked_products: Products that won't be changed
            exclude_categories: Additional categories to exclude from refresh

        Returns:
            Updated bundle recommendation
        """
        exclude_categories = exclude_categories or set()

        # Unlock locked products temporarily for re-recommendation
        # but ensure they stay in the final bundle
        refreshed = self.recommend_bundle(
            products,
            user_themes,
            user_budget,
            user_categories - exclude_categories,
            locked_products
        )

        return refreshed


def main():
    """Test the Recommendation Agent."""
    agent = RecommendationAgent()

    # Sample product data (with extraction results)
    sample_products = [
        {
            "sku": "K-26107-LA-0",
            "name": "Entity 60\" x 36\" Alcove Bath",
            "category": "Bathtubs",
            "price": 818.25,
            "color_finish": "White",
            "availability": True,
            "inferred_themes": [
                {"theme": "Modern", "confidence": 0.95},
                {"theme": "Minimalist", "confidence": 0.85}
            ],
            "primary_theme": "Modern"
        },
        {
            "sku": "K-16109-LA-0",
            "name": "Archer Polished Chrome Widespread Faucet",
            "category": "Faucets",
            "price": 349.00,
            "color_finish": "Polished Chrome",
            "availability": True,
            "inferred_themes": [
                {"theme": "Classic", "confidence": 0.8},
                {"theme": "Transitional", "confidence": 0.7}
            ],
            "primary_theme": "Classic"
        },
        {
            "sku": "K-2346-1-0",
            "name": "Memoirs Pedestal Sink Basin",
            "category": "Basins",
            "price": 279.50,
            "color_finish": "White",
            "availability": True,
            "inferred_themes": [
                {"theme": "Classic", "confidence": 0.9}
            ],
            "primary_theme": "Classic"
        },
        {
            "sku": "K-3977-1-0",
            "name": "Wellworth 1.6 GPF Toilet",
            "category": "Toilets",
            "price": 189.99,
            "color_finish": "White",
            "availability": True,
            "inferred_themes": [
                {"theme": "Modern", "confidence": 0.75},
                {"theme": "Minimalist", "confidence": 0.7}
            ],
            "primary_theme": "Modern"
        },
    ]

    # User input
    user_themes = ["Modern", "Minimalist"]
    user_budget = 2000.00
    user_categories = {"Bathtubs", "Faucets", "Basins", "Toilets"}

    print("=" * 80)
    print("RECOMMENDATION AGENT - BUNDLE RECOMMENDATION TEST")
    print("=" * 80)
    print(f"\nUser Input:")
    print(f"  Themes: {user_themes}")
    print(f"  Budget: ${user_budget:.2f}")
    print(f"  Categories: {user_categories}")

    # Get initial recommendation
    result = agent.recommend_bundle(
        sample_products,
        user_themes,
        user_budget,
        user_categories
    )

    print(f"\nRecommended Bundle:")
    print(f"  Total Price: ${result['total_price']:.2f}")
    print(f"  Within Budget: {result['within_budget']}")
    print(f"\nProducts:")
    for i, product in enumerate(result['recommended_bundle'], 1):
        print(f"  {i}. {product['name']}")
        print(f"     Price: ${product['price']:.2f}")
        print(f"     Primary Theme: {product.get('primary_theme')}")


if __name__ == "__main__":
    main()
