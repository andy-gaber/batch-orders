This program was developed for an e-commerce retailer that sells products on Amazon, eBay, and Shopify. The company utilizes ShipStation, a web-based shipping platform, to import, manage, and ship all orders from each of these selling channels.

The program makes HTTP requests to ShipStation’s API to import all awaiting shipment order data, sorts these orders alphanumerically via Stock Keeping Unit (SKU), then produces a “pick list” used pick, pack, and process the orders in batches. The main purpose of this program is to sort the multitude of new awaiting shipment orders alphanumerically by SKU, which enables batch picking and ultimately optimizes order processing.

New orders are detected by their Order ID, which is a unique identifier generated by each selling channel, and each Order ID is stored in an external text file after the order is processed.

When new awaiting shipment order data is requested, and each order’s Order ID is referenced with the Order ID’s stored in the text file. If the order is flagged as new its metadata is parsed and the item’s SKU and quantity are added to a hash table that maps the current batch of SKU’s to their respective quantities. Also, the order’s Order ID is added to the external text file to mark it as processed.

After all awaiting shipment orders have been traversed, the hash table is sorted by its keys (i.e. alphanumerically via SKU), then each SKU, with its respective quantity, is written to an external text file. This file is the current batch “pick list”.

In addition, ShipStation’s API provides an item’s image URL that redirects to the item image saved in ShipStation's database. This URL is used by the program to create an additional HTML file that contains each new awaiting shipment item’s image URL that can be referenced to confirm item correctness when picking new orders.

The program is automated to recur at regular intervals throughput the day to promptly fetch new orders waiting to be shipped, and Python’s Simple Mail Transfer Protocol (SMTP) library is implemented to send e-mails at each interval with the current batch of new orders for immediate processing.
