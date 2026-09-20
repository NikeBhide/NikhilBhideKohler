"""
KOHLER Bathroom Designer - Flask API Server
Exposes agents as HTTP endpoints for React frontend
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from kohler_system import KohlerBathroomDesigner
import json
import os

# Explicitly set instance_path to avoid Flask's auto_find_instance_path(),
# which calls pkgutil.get_loader() -- removed in Python 3.14 and causes
# "AttributeError: module 'pkgutil' has no attribute 'get_loader'".
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, instance_path=os.path.join(_BASE_DIR, "instance"))
CORS(app)

# Initialize system
designer = None

def init_designer():
    """Initialize the designer system with product data."""
    global designer
    # KohlerBathroomDesigner loads real products from backend/data/products.json
    # via _load_products() when no products_data is passed in.
    designer = KohlerBathroomDesigner()

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})

@app.route('/api/themes', methods=['GET'])
def get_themes():
    """Get available design themes."""
    try:
        themes = designer.get_theme_options()
        return jsonify({
            "success": True,
            "themes": themes,
            "theme_keywords": designer.get_theme_keywords(),
            "count": len(themes)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get available product categories."""
    try:
        categories = designer.get_category_options()
        return jsonify({
            "success": True,
            "categories": categories,
            "count": len(categories)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/infer-themes', methods=['POST'])
def infer_themes_endpoint():
    """
    Infer design themes from a user's freeform description of their vision.

    Request body: {"text": "I want something modern and spa-like with warm tones"}
    """
    try:
        data = request.json or {}
        text = (data.get("text") or "").strip()
        if not text:
            return jsonify({"success": False, "error": "text required"}), 400

        result = designer.infer_themes_from_text(text)
        return jsonify({
            "success": True,
            "inferred_themes": result["inferred_themes"],
            "primary_theme": result["primary_theme"],
            "low_confidence": result.get("low_confidence", False)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/recommend', methods=['POST'])
def recommend():
    """
    Get bathroom bundle recommendation.

    Request body:
    {
        "themes": ["Modern", "Spa"],
        "budget": 5000,
        "width": 60,
        "depth": 80,
        "categories": ["Toilets", "Basins", "Faucets"],
        "locked_products": []
    }
    """
    try:
        data = request.json

        # Validate input
        if not data.get("themes"):
            return jsonify({"success": False, "error": "themes required"}), 400
        if not data.get("budget"):
            return jsonify({"success": False, "error": "budget required"}), 400
        if not data.get("width") or not data.get("depth"):
            return jsonify({"success": False, "error": "width and depth required"}), 400
        if not data.get("categories"):
            return jsonify({"success": False, "error": "categories required"}), 400

        # Get recommendation
        result = designer.recommend_bathroom(
            user_themes=data["themes"],
            user_budget=float(data["budget"]),
            bathroom_width=int(data["width"]),
            bathroom_depth=int(data["depth"]),
            selected_categories=set(data["categories"]),
            locked_products=data.get("locked_products", [])
        )

        # Clean up result for JSON serialization
        bundle = result["recommendation"]["bundle"]
        cleaned_bundle = []
        for product in bundle:
            cleaned_bundle.append({
                "sku": product.get("sku"),
                "name": product.get("name"),
                "category": product.get("category"),
                "price": product.get("price"),
                "color_finish": product.get("color_finish"),
                "primary_theme": product.get("primary_theme"),
                "inferred_themes": product.get("inferred_themes", []),
                "url": product.get("url"),
                "image_url": product.get("image_url")
            })

        return jsonify({
            "success": True,
            "bundle": cleaned_bundle,
            "total_price": result["recommendation"]["total_price"],
            "within_budget": result["recommendation"]["within_budget"],
            "primary_theme": result["recommendation"]["primary_theme"],
            "placement_map": {k: {"x": v[0], "y": v[1]} for k, v in result["placement"]["placement_map"].items()},
            "grid_visualization": result["placement"]["grid_visualization"],
            "entrance": result["placement"].get("entrance"),
            "violations": result["constraints"]["violations"],
            "all_constraints_satisfied": result["constraints"]["all_satisfied"],
            "filled_categories": result["recommendation"].get("filled_categories", []),
            "unfilled_categories": result["recommendation"].get("unfilled_categories", []),
            "unfilled_details": result["recommendation"].get("unfilled_details", {}),
            "remaining_budget": result["recommendation"].get("remaining_budget", 0),
            "requested_budget": result["recommendation"].get("requested_budget", 0)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/refresh', methods=['POST'])
def refresh():
    """
    Refresh bundle for unlocked categories.

    Request body:
    {
        "themes": ["Modern", "Spa"],
        "budget": 5000,
        "width": 60,
        "depth": 80,
        "categories": ["Toilets", "Basins", "Faucets"],
        "locked_products": ["K-3977-1-0"],
        "refresh_categories": ["Basins", "Faucets"]
    }
    """
    try:
        data = request.json

        result = designer.refresh_recommendation(
            user_themes=data["themes"],
            user_budget=float(data["budget"]),
            bathroom_width=int(data["width"]),
            bathroom_depth=int(data["depth"]),
            selected_categories=set(data["categories"]),
            locked_products=data.get("locked_products", []),
            refresh_categories=set(data.get("refresh_categories", []))
        )

        bundle = result["recommendation"]["bundle"]
        cleaned_bundle = []
        for product in bundle:
            cleaned_bundle.append({
                "sku": product.get("sku"),
                "name": product.get("name"),
                "category": product.get("category"),
                "price": product.get("price"),
                "color_finish": product.get("color_finish"),
                "primary_theme": product.get("primary_theme"),
                "inferred_themes": product.get("inferred_themes", []),
                "url": product.get("url"),
                "image_url": product.get("image_url")
            })

        return jsonify({
            "success": True,
            "bundle": cleaned_bundle,
            "total_price": result["recommendation"]["total_price"],
            "within_budget": result["recommendation"]["within_budget"],
            "primary_theme": result["recommendation"]["primary_theme"],
            "placement_map": {k: {"x": v[0], "y": v[1]} for k, v in result["placement"]["placement_map"].items()},
            "grid_visualization": result["placement"]["grid_visualization"],
            "entrance": result["placement"].get("entrance"),
            "violations": result["constraints"]["violations"],
            "all_constraints_satisfied": result["constraints"]["all_satisfied"],
            "filled_categories": result["recommendation"].get("filled_categories", []),
            "unfilled_categories": result["recommendation"].get("unfilled_categories", []),
            "unfilled_details": result["recommendation"].get("unfilled_details", {}),
            "remaining_budget": result["recommendation"].get("remaining_budget", 0),
            "requested_budget": result["recommendation"].get("requested_budget", 0)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/products/search', methods=['GET'])
def search_products():
    """
    Search products by theme or category.

    Query params:
    - theme: Filter by design theme
    - category: Filter by product category
    """
    try:
        theme = request.args.get("theme")
        category = request.args.get("category")

        products = designer.search_products(theme=theme, category=category)

        cleaned_products = []
        for product in products:
            cleaned_products.append({
                "sku": product.get("sku"),
                "name": product.get("name"),
                "category": product.get("category"),
                "price": product.get("price"),
                "color_finish": product.get("color_finish"),
                "primary_theme": product.get("primary_theme"),
                "inferred_themes": product.get("inferred_themes", [])
            })

        return jsonify({
            "success": True,
            "products": cleaned_products,
            "count": len(cleaned_products)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "success": False,
        "error": "Endpoint not found"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500

if __name__ == '__main__':
    init_designer()
    app.run(debug=True, host='localhost', port=5000)
