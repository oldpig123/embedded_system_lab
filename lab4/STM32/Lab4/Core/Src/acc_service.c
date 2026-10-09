/*
 * acc_service.c
 *
 *  Created on: 2026年10月9日
 *      Author: 102he
 */

#include "acc_service.h"
#include "bluenrg_gatt_aci.h"

#define COPY_UUID_128(uuid_struct, uuid_15, uuid_14, uuid_13, uuid_12, uuid_11, uuid_10, uuid_9, uuid_8, uuid_7, uuid_6, uuid_5, uuid_4, uuid_3, uuid_2, uuid_1, uuid_0) \
do {\
    uuid_struct[0] = uuid_0; uuid_struct[1] = uuid_1; uuid_struct[2] = uuid_2; uuid_struct[3] = uuid_3; \
        uuid_struct[4] = uuid_4; uuid_struct[5] = uuid_5; uuid_struct[6] = uuid_6; uuid_struct[7] = uuid_7; \
            uuid_struct[8] = uuid_8; uuid_struct[9] = uuid_9; uuid_struct[10] = uuid_10; uuid_struct[11] = uuid_11; \
                uuid_struct[12] = uuid_12; uuid_struct[13] = uuid_13; uuid_struct[14] = uuid_14; uuid_struct[15] = uuid_15; \
}while(0)

#define COPY_ACC_SERVICE_UUID(uuid_struct) COPY_UUID_128(uuid_struct,0x0a,0x38,0xe7,0x01,0x05,0x11,0x49,0xc1,0xba,0x27,0x5f,0xfb,0x91,0x12,0x42,0xa4)
#define COPY_ACC_XYZ_CHAR_UUID(uuid_struct) COPY_UUID_128(uuid_struct,0x0a,0x38,0xe7,0x02,0x05,0x11,0x49,0xc1,0xba,0x27,0x5f,0xfb,0x91,0x12,0x42,0xa4)
#define COPY_ACC_FREQ_CHAR_UUID(uuid_struct) COPY_UUID_128(uuid_struct,0x0a,0x38,0xe7,0x03,0x05,0x11,0x49,0xc1,0xba,0x27,0x5f,0xfb,0x91,0x12,0x42,0xa4)

uint16_t accServHandle;
uint16_t accCharHandle;
uint16_t freqCharHandle;
volatile uint8_t acc_freq_hz = 2;

tBleStatus Add_Acc_Service(void) {
	tBleStatus ret;
	uint8_t uuid[16];

	COPY_ACC_SERVICE_UUID(uuid);
	ret = aci_gatt_add_serv(UUID_TYPE_128, uuid, PRIMARY_SERVICE, 6, &accServHandle);
	if (ret != BLE_STATUS_SUCCESS) {
		return ret;
	}

	COPY_ACC_XYZ_CHAR_UUID(uuid);
	ret = aci_gatt_add_char(accServHandle, UUID_TYPE_128, uuid, 6, CHAR_PROP_NOTIFY, ATTR_PERMISSION_NONE, GATT_DONT_NOTIFY_EVENTS, 16, CHAR_VALUE_LEN_CONSTANT, &accCharHandle);
	if (ret != BLE_STATUS_SUCCESS) {
		return ret;
	}

	COPY_ACC_FREQ_CHAR_UUID(uuid);
	ret = aci_gatt_add_char(accServHandle, UUID_TYPE_128, uuid, 1, CHAR_PROP_WRITE | CHAR_PROP_WRITE_WITHOUT_RESP, ATTR_PERMISSION_NONE, GATT_NOTIFY_ATTRIBUTE_WRITE, 16, CHAR_VALUE_LEN_CONSTANT, &freqCharHandle);
	if (ret != BLE_STATUS_SUCCESS) {
		return ret;
	}

	return BLE_STATUS_SUCCESS;
}


tBleStatus Acc_Service_Notify(const int16_t xyz[3]) {
	return aci_gatt_update_char_value(accServHandle, accCharHandle, 0, 6, xyz);
}

void Acc_Service_Attr_Modified(uint16_t attr_handle, uint8_t data_length, const uint8_t *att_data) {
	if (attr_handle == freqCharHandle + 1 && data_length == 1 && att_data[0] > 0) {
		acc_freq_hz = att_data[0];
	}
}

