# Table Documentation

## orders
Keywords: 销售额, GMV, 订单量, 客单价, 最近, 趋势, paid, status, order_date

Order header table. Use it for order status, order date, buyer, and order-level lifecycle filtering.

Fields:

- `id`: Primary key for an order.
- `user_id`: References `users.id`.
- `order_date`: Date the order was placed; use this for BI time windows.
- `status`: Order lifecycle status. P0 values are `paid`, `cancelled`, and `refunded`.

## order_items
Keywords: 销售额, GMV, 商品, 销量, quantity, unit_price, 明细

Order line-item table. Use it for item quantity, purchase-time unit price, and product-level sales analysis.

Fields:

- `id`: Primary key for an order item.
- `order_id`: References `orders.id`.
- `product_id`: References `products.id`.
- `quantity`: Number of units purchased.
- `unit_price`: Transaction-time unit price; use this for GMV instead of product list price.

## products
Keywords: 商品, product, Top, 销量, 销售额, GMV

Product dimension table. Use it to display product names and connect items to categories.

Fields:

- `id`: Primary key for a product.
- `product_name`: Human-readable product name.
- `category_id`: References `categories.id`.
- `price`: Current catalog price. Do not use it for historical GMV.

## categories
Keywords: 品类, category, 类目, 销售额, GMV

Category dimension table. Use it for category-level rollups and comparisons.

Fields:

- `id`: Primary key for a category.
- `category_name`: Human-readable category name.

## users
Keywords: 地区, 城市, 注册, cohort

User dimension table. Use it for aggregated buyer attributes and cohort analysis.

Fields:

- `id`: Primary key for a user.
- `name`: Display name.
- `email`: Sensitive contact field; do not export in BI answer SQL.
- `phone`: Sensitive contact field; do not export in BI answer SQL.
- `city`: User city.
- `created_at`: User registration timestamp.

## marketing_campaigns
Keywords: campaign, 渠道, Paid Search, ROI, CAC, 投放, 营销

Campaign metadata table. Use it to identify campaign channel, owner, objective, and active date range.

Fields:

- `id`: Primary key for a campaign.
- `campaign_name`: Human-readable campaign name.
- `channel`: Marketing channel such as `Paid Search`, `Promotion`, `Email`, or `Organic`.
- `owner`: Internal team responsible for the campaign.
- `start_date`: Campaign start date.
- `end_date`: Campaign end date.
- `objective`: Campaign business objective.

## campaign_daily_metrics
Keywords: campaign, ROI, CAC, spend, impressions, clicks, attributed GMV, net GMV

Daily campaign performance fact table. Use it for marketing spend, attributed order, attributed GMV, net GMV, CAC, and ROI analysis.

Fields:

- `id`: Primary key for a daily metric row.
- `campaign_id`: References `marketing_campaigns.id`.
- `promotion_id`: Optional reference to `promotion_events.id` when the campaign is tied to a promotion.
- `metric_date`: Daily metric date.
- `impressions`: Campaign impressions.
- `clicks`: Campaign clicks.
- `spend`: Daily marketing spend.
- `attributed_orders`: Orders attributed to the campaign.
- `attributed_gmv`: Gross GMV attributed to the campaign.
- `net_gmv`: GMV after refund, discount, or quality adjustments for scenario analysis.

## traffic_sessions
Keywords: sessions, conversion, checkout conversion, 城市, 流量, 转化率

Daily traffic funnel table by city, channel, and landing category. Use it for session stability, add-to-cart, checkout, and paid-order conversion analysis.

Fields:

- `id`: Primary key for a traffic row.
- `session_date`: Daily traffic date.
- `city`: Visitor city.
- `channel`: Traffic source channel.
- `landing_category_name`: Landing category for the session group.
- `sessions`: Session count.
- `add_to_carts`: Sessions that added an item to cart.
- `checkout_starts`: Sessions that started checkout.
- `paid_orders`: Paid orders from the session group.

## inventory_snapshots
Keywords: inventory, stock, available quantity, inbound, 缺货, 库存

Daily product inventory snapshot table. Use it to inspect available quantity and inbound quantity around demand or stockout anomalies.

Fields:

- `id`: Primary key for an inventory snapshot.
- `snapshot_date`: Snapshot date.
- `product_id`: References `products.id`.
- `product_name`: Product name copied for readable scenario queries.
- `category_name`: Product category name copied for readable scenario queries.
- `available_quantity`: Sellable inventory available that day.
- `inbound_quantity`: Expected inbound replenishment quantity.

## stockout_events
Keywords: stockout, 缺货, lost sales, inventory risk

Product-level stockout event table. Use it to explain lost sales, demand suppression, fulfillment delay, and GMV decline.

Fields:

- `id`: Primary key for a stockout event.
- `product_id`: References `products.id`.
- `product_name`: Product name.
- `category_name`: Product category name.
- `start_date`: First stockout date.
- `end_date`: Last stockout date.
- `lost_sales_estimate`: Estimated GMV impact of the stockout.

## refund_requests
Keywords: refund, 退款, 售后, risk, net GMV

Refund request fact table. Use it for refund-rate, refund reason, quality risk, and net GMV quality analysis.

Fields:

- `id`: Primary key for a refund request.
- `request_date`: Refund request date.
- `order_id`: References `orders.id`.
- `product_id`: References `products.id`.
- `product_name`: Product name.
- `category_name`: Product category name.
- `reason`: Refund reason.
- `refund_amount`: Requested refund amount.
- `status`: Refund lifecycle status: `requested`, `approved`, or `rejected`.

## product_reviews
Keywords: review, rating, sentiment, 评价, 负面评价, 商品风险

Product review table. Use it to connect high-GMV products to rating, sentiment, and topic-level quality risk.

Fields:

- `id`: Primary key for a product review.
- `review_date`: Review date.
- `product_id`: References `products.id`.
- `product_name`: Product name.
- `rating`: 1 to 5 star rating.
- `sentiment`: `positive`, `neutral`, or `negative`.
- `topic`: Review topic such as quality, delivery, or price dispute.

## pricing_events
Keywords: price, discount, promotion, AOV, margin, 价格

Product price-change table. Use it to explain promotion windows, AOV changes, and margin pressure.

Fields:

- `id`: Primary key for a pricing event.
- `product_id`: References `products.id`.
- `product_name`: Product name.
- `start_date`: Price event start date.
- `end_date`: Price event end date.
- `old_price`: Previous catalog or campaign price.
- `new_price`: New price during the event window.
- `reason`: Business reason for the price change.

## promotion_events
Keywords: promotion, 促销, discount, AOV, order count, net GMV

Promotion metadata table. Use it to identify promotion windows, target categories or products, discount type, and expected margin impact.

Fields:

- `id`: Primary key for a promotion event.
- `promotion_name`: Human-readable promotion name.
- `start_date`: Promotion start date.
- `end_date`: Promotion end date.
- `discount_type`: Promotion type such as bundle discount or coupon.
- `target_scope`: Whether the promotion targets a category or product.
- `target_category_name`: Category target when applicable.
- `target_product_id`: Product target when applicable.
- `expected_margin_impact`: Expected margin impact ratio; negative values indicate margin pressure.

## fulfillment_events
Keywords: fulfillment, delivery, delay, logistics, 履约, 延迟

Fulfillment event table. Use it to connect stockouts, delivery delays, refund requests, and city-level operational issues.

Fields:

- `id`: Primary key for a fulfillment event.
- `event_date`: Fulfillment event date.
- `order_id`: References `orders.id`.
- `product_id`: References `products.id`.
- `product_name`: Product name.
- `city`: Destination city.
- `delay_days`: Delivery delay in days.
- `delivery_status`: Delivery status such as `delivered` or `delayed`.
- `issue_reason`: Logistics or fulfillment issue reason.
