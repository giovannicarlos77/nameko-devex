## Code Challenge: Understanding Performance Degradation

### Why is performance degrading as the test run longer?

Performance degradation becomes apparent as the test runs for an extended duration. This deterioration in performance is attributed to the system's operational behavior. Specifically, when making GET or POST requests to the `/orders` endpoint, the gateway triggers a Remote Procedure Call (RPC) to the Products service. This RPC request is responsible for fetching the complete list of products stored in the database. Initially, this approach may seem acceptable, serving validation purposes and enhancing responses with product details.

However, the issue arises as the database accumulates a larger number of products over time. The process of retrieving the entire product list becomes progressively time-consuming. The prolonged retrieval time is a direct consequence of the growing volume of products within the database. As a result, the Products service responds more slowly due to the increased load, ultimately leading to a noticeable degradation in the overall system's performance.

### How do you fix it?

To tackle this performance challenge, you can enhance the product service by introducing a filtering mechanism. This filtering capability can be crafted to seek out particular `product_ids` and retrieve exclusively those `product_ids` linked to the orders needing validation or product information enrichment. This approach helps circumvent the need for fetching the entire product catalog needlessly, resulting in a more streamlined and responsive system performance.

## Notes
I have implemented pagination in the form of OFFSET and LIMIT, but it's worth mentioning that the subsequent instructions do not cover this aspect. Due to this, I have commented out the pagination-related code to keep the focus on the instructions that are within the current scope.

As a result, I've commented out the implementation of pagination in the following instructions. Additionally, I've also commented out the retrieval of all orders in the `next-bzt.yml` file. This decision was made to prevent delays caused by attempting to retrieve all orders without pagination or another mechanism in place.
