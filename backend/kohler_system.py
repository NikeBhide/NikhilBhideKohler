"""
KOHLER Bathroom Designer - System Orchestrator
Ties together Extraction, Recommendation, and Placement agents
"""

import json
import os
from typing import List, Dict, Set, Optional
from extraction_agent import ExtractionAgent
from recommendation_agent import RecommendationAgent
from placement_agent import PlacementAgent


class KohlerBathroomDesigner:
    """
    Main orchestrator that coordinates all three agents to provide
    end-to-end bathroom design recommendations.
    """

    def __init__(self, products_data: List[Dict] = None):
        """
        Initialize the system with all agents.

        Args:
            products_data: Pre-loaded product catalog (or will load from JSON)
        """
        self.extraction_agent = ExtractionAgent()
        self.recommendation_agent = RecommendationAgent()
        self.placement_agent = PlacementAgent()

        # Load or use provided product data
        self.products = products_data or self._load_products()

        # Enrich products with theme inferences
        self.products = self.extraction_agent.process_products(self.products)

    def _load_products(self) -> List[Dict]:
        """Load product data from backend/data/products.json, if present."""
        data_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", "products.json"
        )
        if os.path.exists(data_path):
            with open(data_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def recommend_bathroom(
        self,
        user_themes: List[str],
        user_budget: float,
        bathroom_width: int,
        bathroom_depth: int,
        selected_categories: Set[str],
        locked_products: List[str] = None
    ) -> Dict:
        """
        Generate a complete bathroom design recommendation.

        Args:
            user_themes: User's selected design themes
            user_budget: Total budget for bathroom
            bathroom_width: Bathroom width in inches
            bathroom_depth: Bathroom depth in inches
            selected_categories: Product categories to include
            locked_products: List of SKUs user has locked

        Returns:
            Dict with recommended_bundle, placement_map, visualization, violations
        """

        # Step 1: Recommendation Agent - Find best bundle
        locked_products_data = []
        if locked_products:
            locked_products_data = [
                p for p in self.products if p.get("sku") in locked_products
            ]

        recommendation_result = self.recommendation_agent.recommend_bundle(
            self.products,
            user_themes,
            user_budget,
            selected_categories,
            locked_products_data
        )

        bundle = recommendation_result["recommended_bundle"]

        # Step 2: Placement Agent - Arrange on grid
        grid = self.placement_agent.create_grid(bathroom_width, bathroom_depth)
        placement_result = self.placement_agent.auto_place_bundle(grid, bundle)

        # Step 3: Prepare output
        return {
            "status": "success" if placement_result["success"] else "partial",
            "recommendation": {
                "bundle": bundle,
                "total_price": recommendation_result["total_price"],
                "within_budget": recommendation_result["within_budget"],
                "primary_theme": self._determine_primary_theme(bundle),
                "filled_categories": recommendation_result.get("filled_categories", []),
                "unfilled_categories": recommendation_result.get("unfilled_categories", []),
                "unfilled_details": recommendation_result.get("unfilled_details", {}),
                "remaining_budget": recommendation_result.get("remaining_budget", 0),
                "requested_budget": user_budget,
            },
            "placement": {
                "placement_map": placement_result["placement_map"],
                "bathroom_dimensions": {
                    "width": bathroom_width,
                    "depth": bathroom_depth,
                },
                "grid_visualization": self.placement_agent.visualize_grid(grid),
                "entrance": placement_result.get("entrance"),
                "floor_rects": placement_result.get("floor_rects", {}),
            },
            "constraints": {
                "violations": placement_result["violations"],
                "all_satisfied": placement_result["success"],
            },
            "alternatives": recommendation_result.get("alternatives", {}),
        }

    def refresh_recommendation(
        self,
        user_themes: List[str],
        user_budget: float,
        bathroom_width: int,
        bathroom_depth: int,
        selected_categories: Set[str],
        locked_products: List[str],
        refresh_categories: Set[str] = None
    ) -> Dict:
        """
        Refresh recommendation for unlocked categories.

        Args:
            user_themes: User's selected design themes
            user_budget: Total budget
            bathroom_width: Bathroom width in inches
            bathroom_depth: Bathroom depth in inches
            selected_categories: All categories to include
            locked_products: SKUs user has locked
            refresh_categories: Specific categories to refresh (or all unlocked)

        Returns:
            Updated recommendation with refreshed products
        """
        refresh_categories = refresh_categories or set()

        locked_products_data = [
            p for p in self.products if p.get("sku") in locked_products
        ]

        # Determine which categories to exclude from refresh
        exclude = set()
        if refresh_categories:
            exclude = selected_categories - refresh_categories

        # Get new recommendation
        recommendation_result = self.recommendation_agent.refresh_bundle(
            self.products,
            user_themes,
            user_budget,
            selected_categories,
            locked_products_data,
            exclude_categories=exclude
        )

        bundle = recommendation_result["recommended_bundle"]

        # Place on grid
        grid = self.placement_agent.create_grid(bathroom_width, bathroom_depth)
        placement_result = self.placement_agent.auto_place_bundle(grid, bundle)

        return {
            "status": "success" if placement_result["success"] else "partial",
            "recommendation": {
                "bundle": bundle,
                "total_price": recommendation_result["total_price"],
                "within_budget": recommendation_result["within_budget"],
                "primary_theme": self._determine_primary_theme(bundle),
                "filled_categories": recommendation_result.get("filled_categories", []),
                "unfilled_categories": recommendation_result.get("unfilled_categories", []),
                "unfilled_details": recommendation_result.get("unfilled_details", {}),
                "remaining_budget": recommendation_result.get("remaining_budget", 0),
                "requested_budget": user_budget,
            },
            "placement": {
                "placement_map": placement_result["placement_map"],
                "bathroom_dimensions": {
                    "width": bathroom_width,
                    "depth": bathroom_depth,
                },
                "grid_visualization": self.placement_agent.visualize_grid(grid),
                "entrance": placement_result.get("entrance"),
                "floor_rects": placement_result.get("floor_rects", {}),
            },
            "constraints": {
                "violations": placement_result["violations"],
                "all_satisfied": placement_result["success"],
            },
        }

    def _determine_primary_theme(self, bundle: List[Dict]) -> str:
        """Determine the primary theme for the entire bundle."""
        theme_counts = {}

        for product in bundle:
            for theme_obj in product.get("inferred_themes", []):
                theme = theme_obj["theme"]
                theme_counts[theme] = theme_counts.get(theme, 0) + 1

        if not theme_counts:
            return "Contemporary"

        return max(theme_counts, key=theme_counts.get)

    def get_theme_options(self) -> List[str]:
        """Get list of available themes."""
        return list(self.extraction_agent.themes.keys())

    def get_theme_keywords(self) -> Dict[str, List[str]]:
        """
        A few descriptive keywords per theme, so the frontend can explain
        *why* a theme was chosen instead of just naming it.
        """
        return {
            name: data.get("keywords", [])[:4]
            for name, data in self.extraction_agent.themes.items()
        }

    def infer_themes_from_text(self, text: str) -> Dict:
        """
        Infer design themes from a user's freeform description of their
        vision (e.g. "I want something modern and spa-like"), reusing the
        exact same keyword/pattern matching used to tag real products.

        guarantee_result=True: a person's own casual description is much
        shorter than a product's catalog copy, so it often won't clear the
        normal confidence bar. Rather than reporting no match and leaving
        them with nothing, this always returns a best-guess theme (flagged
        via `low_confidence` when it's a guess rather than a real match) so
        the agent has something concrete to say back, while still letting
        the person pick a different style afterward.
        """
        return self.extraction_agent.infer_themes({"name": "", "description": text}, guarantee_result=True)

    def get_category_options(self) -> List[str]:
        """Get list of available product categories."""
        categories = set()
        for product in self.products:
            cat = product.get("category")
            if cat:
                categories.add(cat)
        return sorted(list(categories))

    def search_products(self, theme: str = None, category: str = None) -> List[Dict]:
        """
        Search products by theme or category.

        Args:
            theme: Filter by design theme
            category: Filter by product category

        Returns:
            List of matching products
        """
        results = self.products.copy()

        if theme:
            results = [
                p for p in results
                if any(t["theme"] == theme for t in p.get("inferred_themes", []))
            ]

        if category:
            results = [p for p in results if p.get("category") == category]

        return results


def main():
    """Test the complete system."""

    # Sample product data for testing
    sample_products = [
        {
            "sku": "K-26107-LA-0",
            "name": "Entity 60\" x 36\" Alcove Bath",
            "category": "Bathtubs",
            "price": 818.25,
            "color_finish": "White",
            "availability": True,
            "dimensions": {"width_inches": 60, "depth_inches": 36},
            "description": "Defined by crisp lines and a clean, simple aesthetic, the KOHLER Entity bath complements a wide range of design languages.",
        },
        {
            "sku": "K-3977-1-0",
            "name": "Wellworth 1.6 GPF Toilet",
            "category": "Toilets",
            "price": 189.99,
            "color_finish": "White",
            "availability": True,
            "dimensions": {"width_inches": 16, "depth_inches": 28},
            "description": "Reliable, efficient toilet with 1.6 GPF water saving performance.",
        },
        {
            "sku": "K-2346-1-0",
            "name": "Memoirs Pedestal Sink",
            "category": "Basins",
            "price": 279.50,
            "color_finish": "White",
            "availability": True,
            "dimensions": {"width_inches": 24, "depth_inches": 18},
            "description": "Classic design with refined details. Perfect for traditional and transitional bathrooms.",
        },
        {
            "sku": "K-16109-LA-0",
            "name": "Archer Polished Chrome Faucet",
            "category": "Faucets",
            "price": 349.00,
            "color_finish": "Polished Chrome",
            "availability": True,
            "dimensions": {"width_inches": 8, "depth_inches": 4},
            "description": "Taking its design cues from traditional Craftsman furniture, the Archer faucet reveals beveled edges and curved details.",
        },
        {
            "sku": "K-6298-CP-0",
            "name": "Stillness Mirror Cabinet",
            "category": "Cabinets",
            "price": 449.99,
            "color_finish": "Chrome",
            "availability": True,
            "dimensions": {"width_inches": 30, "depth_inches": 6},
            "description": "Modern mirrored cabinet with clean lines and sleek contemporary design.",
        },
    ]

    # Initialize system
    system = KohlerBathroomDesigner(sample_products)

    print("=" * 80)
    print("KOHLER BATHROOM DESIGNER - END-TO-END TEST")
    print("=" * 80)

    # User input
    user_themes = ["Modern", "Minimalist"]
    user_budget = 2500.00
    bathroom_width = 60
    bathroom_depth = 80
    selected_categories = {"Bathtubs", "Toilets", "Basins", "Faucets", "Cabinets"}

    print(f"\nUser Input:")
    print(f"  Themes: {user_themes}")
    print(f"  Budget: ${user_budget:.2f}")
    print(f"  Bathroom: {bathroom_width}\" × {bathroom_depth}\"")
    print(f"  Categories: {selected_categories}")

    # Get initial recommendation
    result = system.recommend_bathroom(
        user_themes,
        user_budget,
        bathroom_width,
        bathroom_depth,
        selected_categories
    )

    print(f"\n{'=' * 80}")
    print("RECOMMENDATION RESULT")
    print(f"{'=' * 80}")

    print(f"\nStatus: {result['status']}")
    print(f"Total Price: ${result['recommendation']['total_price']:.2f}")
    print(f"Within Budget: {result['recommendation']['within_budget']}")
    print(f"Primary Theme: {result['recommendation']['primary_theme']}")

    print(f"\nRecommended Bundle:")
    for i, product in enumerate(result['recommendation']['bundle'], 1):
        print(f"  {i}. {product['name']}")
        print(f"     Price: ${product['price']:.2f}")
        print(f"     Category: {product['category']}")

    print(f"\nPlacement Constraints:")
    print(f"  All Satisfied: {result['constraints']['all_satisfied']}")
    if result['constraints']['violations']:
        print(f"  Violations:")
        for violation in result['constraints']['violations']:
            print(f"    - {violation}")

    print(f"\nGrid Visualization (1st 20 rows):")
    grid_lines = result['placement']['grid_visualization'].split('\n')
    for line in grid_lines[:20]:
        print(f"  {line}")

    print(f"\n{'=' * 80}")
    print("END-TO-END TEST COMPLETE")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
