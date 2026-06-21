# Business Rules

## paid_orders_define_sales
Keywords: 销售额, GMV, 收入, 商品, 品类, 客单价, 订单量

Sales analysis must use paid orders only. Cancelled and refunded orders are not counted as realized GMV, revenue, order count, AOV, product sales, or category sales.

Required SQL filter:

```sql
orders.status = 'paid'
```

## gmv_formula
Keywords: 销售额, GMV, revenue, 商品, 品类, Top

GMV is calculated from order item quantity and unit price at the time of purchase.

Required SQL formula:

```sql
SUM(order_items.quantity * order_items.unit_price)
```

Do not use product list price for historical GMV because `order_items.unit_price` is the transaction-time price.

## date_window_uses_order_date
Keywords: 最近, 天, 月, 趋势, 环比, 同比, order_date

Time-window analysis uses `orders.order_date`. A question such as "最近 30 天" should filter on `orders.order_date` relative to the latest available order date in the ecommerce dataset unless the workflow explicitly receives another analysis date.

## privacy_sensitive_fields
Keywords: 邮箱, email, phone, 电话, sensitive, 隐私

Do not export direct personal contact fields for BI answers. Aggregate user behavior where possible and avoid selecting `users.email` or `users.phone` in final SQL.

## net_gmv_quality
Keywords: net GMV, 净 GMV, 退款, 促销质量, revenue quality

Scenario analysis can compare gross attributed GMV with `campaign_daily_metrics.net_gmv` to detect quality issues from refunds, discounts, or low-margin promotions.

Suggested SQL fields:

```sql
campaign_daily_metrics.attributed_gmv,
campaign_daily_metrics.net_gmv
```

## marketing_roi
Keywords: ROI, 投放回报, Paid Search, spend, 营销效率

Marketing ROI is calculated as attributed GMV divided by campaign spend. A channel can have high GMV while ROI declines if spend grows faster than attributed GMV.

Required SQL formula:

```sql
campaign_daily_metrics.attributed_gmv / campaign_daily_metrics.spend
```

## refund_rate
Keywords: refund rate, 退款率, 售后, 商品风险

Refund-rate analysis should compare refund requests with paid orders or attributed orders for the same product, category, channel, or time window.

Suggested numerator:

```sql
COUNT(refund_requests.id)
```

## checkout_conversion
Keywords: checkout conversion, 转化率, sessions, add_to_cart, checkout

City-level funnel diagnosis should separate overall conversion from checkout conversion. Stable sessions with lower checkout starts or paid orders indicates a funnel-quality issue, not a traffic-volume issue.

Suggested SQL formulas:

```sql
SUM(traffic_sessions.paid_orders) * 1.0 / SUM(traffic_sessions.sessions)
SUM(traffic_sessions.checkout_starts) * 1.0 / SUM(traffic_sessions.add_to_carts)
```

## stockout_impact
Keywords: stockout, 缺货, 库存, GMV 下滑

When category or product GMV declines, check `inventory_snapshots` and `stockout_events` before attributing the decline to demand. Stockout windows can suppress paid orders and cause fulfillment delays or refund pressure.
