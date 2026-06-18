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
