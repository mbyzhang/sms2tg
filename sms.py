import logging
import bitstring
import datetime
import copy

def decode_pdu(data: bytearray):
    result = dict()
    result['type'] = data[0]
    p = 1
    while p < len(data):
        record = data[p]
        length = data[p + 1]
        payload = data[p + 2: p + 2 + length]
        
        # teleservice_identifier
        if record == 0x00: 
            result['teleservice_identifier'] = payload
        # service_category
        elif record == 0x01:
            result['service_category'] = payload
        # originating_address
        elif record == 0x02:
            bits = bitstring.BitArray(bytes=payload)
            number_length = bits[2:10].uint
            number = ''
            for i in range(0, number_length):
                number += str(bits[i * 4 + 10: i * 4 + 14].uint % 10)
            result['source'] = number
        # originating_subaddress
        elif record == 0x03:
            result['originating_subaddress'] = payload
        # destination_address
        elif record == 0x04:
            result['destination_address'] = payload
        # destination_subaddress
        elif record == 0x05:
            result['destination_subaddress'] = payload
        # bearer_reply_option
        elif record == 0x06:
            result['bearer_reply_option'] = payload
        # cause_codes
        elif record == 0x07:
            result['cause_codes'] = payload
        # bearer_data
        elif record == 0x08:
            q = 0
            while q < length:
                bearer_record = payload[q]
                bearer_length = payload[q + 1]
                bearer_payload = payload[q + 2: q + 2 + bearer_length]

                # message_id
                if bearer_record == 0x00:
                    result['message_id'] = bearer_payload
                    result['long_message'] = (bearer_payload[2] & 0b1000 > 0)                        
                # content
                elif bearer_record == 0x01:
                    bits = bitstring.BitArray(bytes=bearer_payload)

                    content_encoding = bits[:5].uint
                    content_length = bits[5:13].uint

                    if result['long_message']:
                        udh_length = bits[13:21].uint
                        udh = bits[21:21 + udh_length * 8].bytes

                        r = 0
                        while r < udh_length:
                            udh_record = udh[r]
                            udh_record_length = udh[r + 1]
                            if udh_record == 0:
                                assert(udh_record_length == 3)
                                result['long_message_ref'] = udh[r + 2]
                                result['long_message_total'] = udh[r + 3]
                                result['long_message_index'] = udh[r + 4]
                            else:
                                logging.warning('Advanced UDH is currently not implemented')
                            r += udh_record_length + 2
                        
                        del bits[13:21 + udh_length * 8]

                    # utf-16
                    if content_encoding == 0x04:
                        content = bits[13:-3].bytes.decode('utf-16-be')
                    # ascii
                    elif content_encoding == 0x02:
                        content = bits[13:13 + content_length * 7]
                        
                        for i in range(0, content_length):
                            content.insert('0b0', i * 8)
                        content = content.bytes.decode('ascii')
                    else:
                        raise Exception('Unexpected encoding')
                    
                    result['content'] = content
                    # TODO
                # timestamp
                elif bearer_record == 0x03:
                    assert(bearer_length == 6)
                    timestamp = list()
                    for i in range(0, 6):
                        timestamp.append(bearer_payload[i] // 16 * 10 + bearer_payload[i] % 16)
                    timestamp[0] += 2000
                    result['timestamp'] = datetime.datetime(timestamp[0], timestamp[1], timestamp[2], timestamp[3], timestamp[4], timestamp[5])
                # reply_option
                elif bearer_record == 0x0a:
                    result['reply_option'] = bearer_payload
                elif bearer_record == 0x0e:
                    bits = bitstring.BitArray(bytes=bearer_payload)
                    number_length = bits[1:9].uint
                    number = ''
                    for i in range(0, number_length):
                        number += str(bits[i * 4 + 9: i * 4 + 13].uint % 10)

                    result['callback_number'] = number
                
                q += bearer_length + 2
        else:
            raise Exception('Unexpected PDU data')
        
        p += length + 2
    return result

long_message_sto = dict()

def decode(pdu, index):
    message = decode_pdu(bytearray.fromhex(pdu))
    if message['long_message']:
        lm_ref = message['long_message_ref']
        lm_total = message['long_message_total']
        lm_index = message['long_message_index']
        logging.info('Received long message ({}/{}) with ref number {}'.format(lm_index, lm_total, lm_ref))
        if lm_ref not in long_message_sto:
            long_message_sto[lm_ref] = {
                'length': 0,
                'content': lm_total * [None],
                'indice': list(),
                'pdu': list()
            }
        long_message_sto[lm_ref]['content'][lm_index - 1] = message['content']
        long_message_sto[lm_ref]['length'] += 1
        long_message_sto[lm_ref]['indice'].append(index)
        long_message_sto[lm_ref]['pdu'].append(pdu)
        if long_message_sto[lm_ref]['length'] == lm_total:
            concated_content = ''.join(long_message_sto[lm_ref]['content'])
            concated_pdu = '\n'.join(long_message_sto[lm_ref]['pdu'])
            indice = long_message_sto[lm_ref]['indice']
            del long_message_sto[lm_ref]

            return {
                'source': message['source'],
                'content': concated_content,
                'timestamp': message['timestamp'],
                'pdu': concated_pdu,
                'indice': indice
            }
        else:
            return None
    else:
        return {
            'source': message['source'],
            'content': message['content'],
            'timestamp': message['timestamp'],
            'pdu': pdu,
            'indice': [index]
        }
