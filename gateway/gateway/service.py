import json

from marshmallow import ValidationError
from nameko import config
from nameko.exceptions import BadRequest
from nameko.rpc import RpcProxy
from werkzeug import Response

from gateway.entrypoints import http
from gateway.exceptions import OrderNotFound, ProductNotFound
from gateway.schemas import CreateOrderSchema, GetOrderSchema, ProductSchema


class GatewayService(object):
    """
    Service acts as a gateway to other services over http.
    """

    name = 'gateway'

    orders_rpc = RpcProxy('orders')
    products_rpc = RpcProxy('products')

    @http(
        "GET", "/products/<string:product_id>",
        expected_exceptions=ProductNotFound
    )
    def get_product(self, request, product_id):
        """Gets product by `product_id`
        """
        product = self.products_rpc.get(product_id)
        return Response(
            ProductSchema().dumps(product).data,
            mimetype='application/json'
        )

    @http(
        "DELETE", "/products/<string:product_id>",
        expected_exceptions=ProductNotFound
    )
    def remove_product(self, request, product_id):
        """Remove product by `product_id`
        """
        product = self.products_rpc.delete(product_id)
        return Response(
            ProductSchema().dumps(product).data,
            mimetype='application/json'
        )

    @http(
        "POST", "/products",
        expected_exceptions=(ValidationError, BadRequest)
    )
    def create_product(self, request):
        """Create a new product - product data is posted as json

        Example request ::

            {
                "id": "the_odyssey",
                "title": "The Odyssey",
                "passenger_capacity": 101,
                "maximum_speed": 5,
                "in_stock": 10
            }


        The response contains the new product ID in a json document ::

            {"id": "the_odyssey"}

        """

        schema = ProductSchema(strict=True)

        try:
            # load input data through a schema (for validation)
            # Note - this may raise `ValueError` for invalid json,
            # or `ValidationError` if data is invalid.
            product_data = schema.loads(request.get_data(as_text=True)).data
        except ValueError as exc:
            raise BadRequest("Invalid json: {}".format(exc))

        # Create the product
        self.products_rpc.create(product_data)
        return Response(
            json.dumps({'id': product_data['id']}), mimetype='application/json'
        )
    
    @http("GET", "/orders/all")
    def list_orders(self, request):
        """List all orders in the database."""
        orders = self._get_all_orders()
        return Response(
            json.dumps(orders),
            mimetype='application/json'
        )

    # def list_orders(self, request):
    #     """Retrieve a list of orders with additional product details from the products-service, supporting pagination.

    #     To retrieve orders with pagination, you can use query parameters:

    #     'page' [integer]: Specifies the page number of the results to fetch. Default is page 1.
    #     'page_size' [integer]: Specifies the number of results per page, with a maximum of 100. Default is 30.
    #     For example:
    #     '/orders?page=2&page_size=60'

    #     The response includes pagination information and the list of orders in a JSON format:
    #     {
    #     "page": 1,
    #     "page_size": 50,
    #     "items": [Order]
    #     }

    #     This allows you to efficiently browse through the list of orders while accessing relevant product details."
    #     """
    #     page = request.args.get('page', default=1, type=int)
    #     page_size = request.args.get('page_size', default=50, type=int)

    #     if page_size > 100:
    #         page_size = 100

    #     list_orders_data = self._list_orders(page, page_size)

    #     return Response(
    #         ListOrdersSchema().dumps(list_orders_data).data,
    #         mimetype='application/json'
    #     )

    # def _list_orders(self, page, page_size):
    #     # Retrieve order data from the orders service using pagination
    #     # Note - the response contains additional information for pagination
    #     # Available keys: [page, page_size, total, items]
    #     result = self.orders_rpc.list_orders(page=page, page_size=page_size)

    #     if len(result['items']) > 0:
    #         # Filter and preload products to fill in order_details data
    #         orders_product_ids = self._extract_product_ids_from_orders(result['items'])
    #         product_map = {prod['id']: prod for prod in self._list_products(orders_product_ids)}

    #         for order in result['items']:
    #             order.update(self._fill_order_details_with_product(order, product_map))

    #     return result
    
    @http("GET", "/orders/<int:order_id>", expected_exceptions=OrderNotFound)
    def get_order(self, request, order_id):
        """Gets the order details for the order given by `order_id`.

        Enhances the order details with full product details from the
        products-service.
        """
        order = self._get_order(order_id)
        return Response(
            GetOrderSchema().dumps(order).data,
            mimetype='application/json'
        )

    def _get_product_ids_from_orders(self, orders):
        all_product_ids = []
        for order in orders:
            order_product_ids = self._get_product_ids_from_order(order)
            all_product_ids.extend(order_product_ids)

        return all_product_ids

    def _get_product_ids_from_order(self, order):
        return [order_detail['product_id'] for order_detail in order['order_details']]

    def _list_products(self, product_ids):
        return self.products_rpc.list(product_ids=product_ids)

    def _fill_order_details_with_product(self, order, product_map):
        # get the configured image root
        image_root = config['PRODUCT_IMAGE_ROOT']

        # Enhance order details with product and image details.
        for item in order['order_details']:
            product_id = item['product_id']

            item['product'] = product_map[product_id]
            # Construct an image url.
            item['image'] = '{}/{}.jpg'.format(image_root, product_id)

        return order
    
    def _get_order(self, order_id):
        order = self.orders_rpc.get_order(order_id)

        # Retrieve all products from the products service
        order_product_ids = self._get_product_ids_from_order(order)
        product_map = {prod['id']: prod for prod in self._list_products(order_product_ids)}

        return self._fill_order_details_with_product(order, product_map)
    
    def _get_all_orders(self):
        # Retrieve order data from the orders service.
        orders = self.orders_rpc.list_orders()

        # Retrieve all products from the products service using filter
        order_product_ids = self._get_product_ids_from_orders(orders)
        product_map = {prod['id']: prod for prod in self._list_products(order_product_ids)}

        for order in orders:
            order.update(self._fill_order_details_with_product(order, product_map))

        return orders

    @http(
        "POST", "/orders",
        expected_exceptions=(ValidationError, ProductNotFound, BadRequest)
    )
    def create_order(self, request):
        """Create a new order - order data is posted as json

        Example request ::

            {
                "order_details": [
                    {
                        "product_id": "the_odyssey",
                        "price": "99.99",
                        "quantity": 1
                    },
                    {
                        "price": "5.99",
                        "product_id": "the_enigma",
                        "quantity": 2
                    },
                ]
            }


        The response contains the new order ID in a json document ::

            {"id": 1234}

        """

        schema = CreateOrderSchema(strict=True)

        try:
            # load input data through a schema (for validation)
            # Note - this may raise `ValueError` for invalid json,
            # or `ValidationError` if data is invalid.
            order_data = schema.loads(request.get_data(as_text=True)).data
        except ValueError as exc:
            raise BadRequest("Invalid json: {}".format(exc))

        # Create the order
        # Note - this may raise `ProductNotFound`
        order = self._create_order(order_data)
        return Response(json.dumps({'id': order['id']}), mimetype='application/json')

    def _create_order(self, order_data):
        # check order product ids are valid using filter
        order_product_ids = self._get_product_ids_from_order(order_data)
        valid_product_ids = {prod['id'] for prod in self._list_products(order_product_ids)}

        for item in order_data['order_details']:
            if item['product_id'] not in valid_product_ids:
                raise ProductNotFound(
                    "Product Id {}".format(item['product_id'])
                )

        # Call orders-service to create the order.
        # Dump the data through the schema to ensure the values are serialized
        # correctly.
        serialized_data = CreateOrderSchema().dump(order_data).data
        return self.orders_rpc.create_order(serialized_data['order_details'])
