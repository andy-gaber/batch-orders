import os
import time
import datetime
import requests
import config
from requests.auth import HTTPBasicAuth
import smtplib
from email.message import EmailMessage

KEY = config.api_key
SECRET = config.api_secret
STORE_ID = config.store_id
EMAIL = config.email_address
PASSWORD = config.password

# Dictionary to contain order information: the item Stock Keeping Unit (SKU) and its quantity.
# key : str (SKU)
# value : str (quantity)
new_orders_dict = {}

# Dictionary to contain an item's image URL.
# key : str (SKU)
# value : str (image URL)
image_dict = {}

# Dictionary to contain individual orders with an item quantity of more than one.
# key : str (order number)
# value : tuple (str (customer name), str (SKU), str (quantity))
item_quantity_more_than_one_dict = {}

# Set of order ID's that will not be processed. Order ID's are string literals.
do_not_pull = set([])

# The order ID file contains previous orders that have been processed. Check the filepath for an order ID text file. If the file does not exist, initialize an empty list to contain order ID's that will be processed. If the file does exist, open it and parse the order ID's contained, then initialize a list and append each order ID to it.
if not os.path.isfile('ORDER_ID_LIST.txt'):
    order_id_list = []  # new order ID's
else:
    with open('ORDER_ID_LIST.txt', 'r') as f:
        order_id_string = f.read()                    # returns a string
        order_id_list = order_id_string.split(',')    # returns a list of parsed strings

# Print date and time as MM/DD/YYYY HH:MM:SS AM/PM
print(datetime.datetime.now().strftime("%m/%d/%Y %I:%M:%S %p") + '\n')

# Dictionary of obsolete SKU's mapped to their updated SKU's.
sku_conversion_dict = {'100-SML':'600-SML', '100-MED':'600-MED', '100-LRG':'600-LRG', '100-XL':'600-XL', '100-2XL':'600-2XL', '100-3XL':'600-3XL', '100-4XL':'600-4XL', '100-5XL':'600-5XL', '110-SML':'610-SML', '110-MED':'610-MED', '110-LRG':'610-LRG', '110-XL':'610-XL', '110-2XL':'610-2XL', '110-3XL':'610-3XL', '110-4XL':'610-4XL', '110-5XL':'610-5XL', '200-SML':'300-SML', '200-MED':'300-MED', '200-LRG':'300-LRG', '200-XL':'300-XL', '200-2XL':'300-2XL', '200-3XL':'300-3XL', '200-4XL':'300-4XL', '200-5XL':'300-5XL', '205-SML':'505-SML', '205-MED':'505-MED', '205-LRG':'505-LRG', '205-XL':'505-XL', '205-2XL':'505-2XL', '205-3XL':'505-3XL', '205-4XL':'505-4XL', '205-5XL':'505-5XL'}

def refresh_store():
    """Refresh the selling platform.

    Import orders from the store connected to ShipStation.
    """
    r = requests.post(f'https://ssapi.shipstation.com/stores/refreshstore?storeId={STORE_ID}', auth=HTTPBasicAuth(KEY, SECRET))

    # If request for store refresh OK pause program for one minute to allow enough time to complete refresh.
    if r.json()['success'] == 'true':
        print('Refreshing Store ...\n')
        time.sleep(60)
    else:
        print('Error With Store Refresh.')

def get_orders(endpoint):
    """Return a list of order objects.

    Return a list of dictionaries, each of which contain an order and its information via keys and values.

    Args:
        endpoint: requests.Response() object.

    Returns:
        A list of dictionaries containing order metadata.
    """
    json_dict = endpoint.json()
    return json_dict['orders']

def populate_dict_with_new_orders(list_of_orders):
    """Add new order items to global dictionary.

    Populate the global dictionary with new order information with key, value pair: str (SKU)), str (quantity).

    Args:
        list_of_orders: List of dictionaries.
    """
    # Print quantity of orders for this store.
    print('THIS STORE HAS: ' + str(len(list_of_orders)) + ' ORDERS\n')

    # Extract relevant information from each new order; add new order ID's to external text file; populate global dictionary with new order information; populate image URL dictionary with new order URL's.
    for order in list_of_orders:
        order_num = order['orderNumber']
        cust_name = order['shipTo']['name']

        # If there is a complication with an order do not add its information to the global dictionary.
        if order_num in do_not_pull:
            print(order_num + ' - DID NOT ADD THESE ITEMS TO NEW ORDERS LIST')
            continue
        print(order_num + ' - ' + cust_name)

        # Append new order ID's to external text file and also to new order id list.
        if order_num not in order_id_list:
            with open('ORDER_ID_LIST.txt', 'a') as f:
                f.write(order_num + ',')
            order_id_list.append(order_num)

            # A list of dictionaries with item information.
            items_list = order['items']

            for item in items_list:
                sku = item['sku']
                name = item['name'] # Item description that we provided.
                quantity = item['quantity']
                img_url = item['imageUrl']

                # Convert obsolete SKU to revised SKU, if necessary.
                if sku in sku_conversion_dict:
                    sku = sku_conversion_dict[sku]

                # If SKU was randomly generated make it intelligible by replacing it with the provided item desciption.
                if sku[:3] == 'wi_':
                    sku = name

                # If item does not have a SKU, assign its SKU as the provided item desciption.
                if sku == '':
                    sku = name

                # Populate / update global dictionary and image URL dictionary with item information only from new orders.
                if sku not in new_orders_dict:
                    new_orders_dict[sku] = quantity
                    image_dict[sku] = img_url
                else:
                    new_orders_dict[sku] += quantity

                # If the customer ordered multiple quantities of this item flag the order to confirm it's correct when packing.
                if int(quantity) > 1:
                    if order_num not in item_quantity_more_than_one_dict:
                        item_quantity_more_than_one_dict[order_num] = [cust_name, [sku], [quantity]]
                    # If the order contains multiple quantities of multiple items, append additional SKU's and corresponding quantities.
                    else:
                        item_quantity_more_than_one_dict[order_num][1].append(sku)  # Index 1 is the SKU list.
                        item_quantity_more_than_one_dict[order_num][2].append(quantity) # Index 2 is the quantity list.

def get_new_orders_list():
    """Return a sorted list of new orders.

    Populate a list with new orders, each order is represented as a tuple of (str (SKU), str (quantity), str (image URL)); then sort the list by SKU.

    Returns:
        A list of tuples containing SKU, quantity, image URL.
    """
    new_orders_list = []

    # Each order added to the list will be a tuple of (str (SKU), str (quantity), str (image URL)).
    for order, quant in new_orders_dict.items():
        item = (order, quant, image_dict[order])
        new_orders_list.append(item)

    # Sort by SKU (index zero of each tuple).
    new_orders_list.sort(key=lambda x: x[0])

    return new_orders_list

def print_quantity_of_orders(await_ship):
    """Print the quantity of orders.

    Args:
        await_ship: List of dictionaries.
    """
    print()
    print('-' * 30)
    print('Awaiting Shipment Total: ' + str(len(await_ship)))
    print('-' * 30)

def write_todays_orders_sorted_file(todays_orders_list):
    """Write new orders string to a file.

    Write the item SKU and its quantity, followed by a newline character, for each order in the sorted list of new orders. If the item's quantity is more than one it will be written, otherwise it will be omitted to signify a single item.

    Args:
        todays_orders_list: List of tuples.
    """
    # Encoding for unicode characters of foreign language alphabet.
    with open('TODAYS_ORDERS.txt', 'w', encoding='utf-8') as f:
        for item in todays_orders_list:
            # Only write the quantity if it is more than one.
            if item[1] > 1:
                f.write(item[0] + ' ... (' + str(item[1]) + ')' + '\n')  # item[0] is SKU, item[1] is quantity
            else:
                f.write(item[0] + '\n')

def write_orders_NEW(new_order_dictionary):
    """Write new orders string to a file.

    Write the item style and a list of its sizes (and quantities), followed by a newline character, for each pair of items in the new_order_dictionary. If the item's quantity is more than one it will be written, otherwise it will be omitted to signify a single item.

    new_order_dictionary : dictionary, key = string, value = string representing integer, or list if strings
    """
    desired_order = {'SM': 1, 'ME': 2, 'LR': 3, 'XL': 4, '2X': 5, '3X': 6, '4X': 7, '5X': 8}

    # Encoding for unicode characters of foreign language alphabet.
    with open('TODAYS_ORDERS_[NEW].txt', 'w', encoding='utf-8') as f:
        for key, value in new_order_dictionary.items():
            # If the hashed value to this item is a List, proceed.
            if type(value) is list:
                value.sort(key=lambda x: desired_order[x[:2]])
                # Add quantity of item to "pick list" only if there is more than one.
                for i in range(len(value)):
                    sku, quant = value[i].split('-')
                    if int(quant) == 1:
                        value[i] = sku
                    else:
                        value[i] = sku + ' (' + quant + ')'
                f.write(key + ' -> ')

                # Add commas as delimiter's, except for last item.
                for i in range(len(value)):
                    if i + 1 == len(value):
                        f.write(str(value[i]))
                    else:
                        f.write(str(value[i]) + ', ')
                f.write('\n')

            else:
                if int(value) > 1:
                    f.write(key + ' ... (' + value + ')' + '\n')
                else:
                    f.write(key + '\n')

def write_todays_orders_HTML_img_file(todays_orders_list):
    """Write new orders string to an HTML file.

    Write the item SKU as a URL link in an HTML file, having the link redirect to the item image saved in ShipStation's database.

    Args:
        todays_orders_list: List of tuples.
    """
    # Encoding for unicode characters of foreign language alphabet.
    with open('HTML_ORDERS.html', 'w', encoding='utf-8') as f:
        for item in todays_orders_list:
            hyperlink = f'<a href="{item[2]}">{item[0]}</a><br>'  # item[2] is image URL, item[0] is SKU
            f.write(hyperlink)

def send_email_with_new_orders():
    """Create and send a text based email containng new orders.
    """
    # Instantiate EmailMessage() object, set subject, set email sender, and set email recipient.
    msg = EmailMessage()
    msg['Subject'] = '[NEW ORDERS]'
    msg['From'] = EMAIL
    msg['To'] = EMAIL

    # Open and parse file containing new orders, set the new orders string as the body of the email message.
    with open('TODAYS_ORDERS.txt', 'r') as f:
        new_orders = f.read()  # Returns a string.
        msg.set_content(new_orders)

    # Connect to Gmail SMTP, log in with email address and password, send email.
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:  # Port 465 for SSL.
        smtp.login(EMAIL, PASSWORD)
        smtp.send_message(msg)

# ============================================================================== #

if __name__ == '__main__':

    minutes_to_sleep = 30  # Length of time to pause program in between runs.

    # Iterates to refresh store, process new order data, write new order files, and send new order email. Loops infinitely and pauses every 30 minutes to process new orders throught the day.
    while True:

        # Import new orders.
        refresh_store()

        # Request endpoint for new orders waiting to be shipped.
        awaiting_shipment_request = requests.get(f'https://ssapi.shipstation.com/orders?orderStatus=awaiting_shipment&storeId={STORE_ID}', auth=HTTPBasicAuth(KEY, SECRET))

        # The new batch of orders metadata.
        awaiting_shipment = get_orders(awaiting_shipment_request)

        # Populate global dictionary with new order information.
        populate_dict_with_new_orders(awaiting_shipment)

        # Display the quantity of orders.
        print_quantity_of_orders(awaiting_shipment)

        # Create list of the new batch of orders, sorted by SKU.
        todays_orders_list = get_new_orders_list()

        #################################################################
        ''' Updated sort function. Previously each individual item was written to an external file, which serves as the "pick list," however this led to two problems:

        1) The "pick list" became very long and filled with a multitude of identical inventory items in various sizes. (Example: 3 smalls, 2 mediums, and 4 XLs; all for the same style).

        2) Due to ASCII, Python's sort function would sort items in an undesirable order. The order would be: 2XL, 3XL, 4XL, 5XL, LRG, MED, SML, XL, and the order I wanted was: SML, MED, LRG, XL, 2XL, 3XL, 4XL, 5XL.

        To solve this I parsed the SKU's in new_orders_list and added all individual item styles to a hash table as a key, and created a list of all the sizes, and their respective quantities, as the value in the hash table. Then I sorted the items in the hash table in the desired order by passing a custom comparator to Python's sort function. This resulted in a "pick list" that was more condensed; each line contained the style and then a list of sizes, which were in the desired order too.
        '''
        new_dict = {}
        for item in todays_orders_list:  # element in todays_order_list: (order, quantity, image link)
            description = item[0]
            quantity = item[1]

            # try: only proceed with SKU's in the form BRAND-STYLE-SIZE (the majority of our inventory).
            try:
                sku, style, size = item[0].split('-')
                # Some random SKU's will pass first try clause, but are not desired BRAND-STYLE-SIZE, here we narrow down further.
                try:
                    if int(style):
                        sku_and_style = sku + '-' + style
                        if sku_and_style not in new_dict:
                            new_dict[sku_and_style] = [size + '-' + str(quantity)]
                        else:
                            new_dict[sku_and_style].append(size + '-' + str(quantity))
                except:
                    new_dict[description] = str(quantity)
            except:
                new_dict[description] = str(quantity)

        write_orders_NEW(new_dict)

        #################################################################

        # Write the sorted list to text file.
        write_todays_orders_sorted_file(todays_orders_list)

        # Write the item's URL image link to HTML file.
        write_todays_orders_HTML_img_file(todays_orders_list)

        # For any individual order that contains an item with a quantity greater than one: print order number, customer name, SKU, and quantity.
        if item_quantity_more_than_one_dict:
            print('\n* ORDERS WITH MORE THAN ONE ITEM QUANTITY:\n')
            for key, value in item_quantity_more_than_one_dict.items():
                print(key) # Key is the order number.
                for item in range(len(value[1])):  # value[1] is a list of SKU's
                    print(value[0])     # value[0] is the customer name.
                    print(value[1][item])  # value[1][item] is the current SKU in the list of SKU's.
                    print(value[2][item])  # value[2][item] is the current quantity in the list of quantities.
                    print()

        # Send email with updated list of new orders.
        send_email_with_new_orders()

        # The global dictionary is populated with new orders. Here we want to set it back to an empty dictionary before the next iteration so it will be populated with only new orders that come in.
        new_orders_dict.clear()

        time.sleep(minutes_to_sleep * 60)  # 30 minutes.
