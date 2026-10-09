/*
 * acc_service.h
 *
 *  Created on: 2026年10月9日
 *      Author: 102he
 */

#include "bluenrg_def.h"

#ifndef INC_ACC_SERVICE_H_
#define INC_ACC_SERVICE_H_

extern volatile uint8_t acc_freq_hz;

tBleStatus Add_Acc_Service(void);
tBleStatus Acc_Service_Notify(const int16_t xyz[3]);
tBleStatus Acc_Service_Motion_Notify(void);
void Acc_Service_Attr_Modified(uint16_t attr_handle, uint8_t data_length, const uint8_t *att_data);

#endif /* INC_ACC_SERVICE_H_ */
