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
