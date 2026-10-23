from src.marketplace_search import MarketplaceItem, handoff_decision


def test_buyer_confirmation_moves_order_to_fulfillment():
    item = MarketplaceItem("asset-7", "Buyer confirmed delivery address", "seller-2", "order-9", "buyer_confirmed")
    assert handoff_decision(item) == "fulfillment"


def test_unconfirmed_content_stays_in_review():
    item = MarketplaceItem("asset-8", "Address needs verification", "seller-2", "order-10", "pending")
    assert handoff_decision(item) == "compliance_review"
