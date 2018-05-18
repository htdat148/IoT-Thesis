//v2 not have ring buffer
#include "main.h"
#include "app/inc/init.h"

// first connect to raspberry, then allow tiva send data to Raspberry
const int Address = 0x10;  // lora address
volatile bool on_connect = false;

bool flagLed1 = false;
bool flagLed2 = false;

uint8_t array_connect[7];
uint8_t array_send[7] = {0};

volatile bool alarmLed1 = false;
volatile bool alarmLed2 = false;

volatile uint32_t timerLed1 = 0;
volatile uint32_t timerLed2 = 0;

typedef struct {
    bool dht11;
}FLAG;
FLAG flag;

typedef enum {
    CONNECT,
    GETDATA,
    CHECKCRC,
    CHECKFRAME} STATE;
STATE state = CONNECT; // first state of state machine

/* define data for ring buffer*/
RINGBUF UART0_RxRingBuff;
#define SIZE 100
uint8_t buffer[SIZE] = {0}; // buffer store data

void UART1_Handler(void) //uart receive timeout 0.1s
{
    uint32_t ui32Status;
    volatile uint8_t data;
    ui32Status = UARTIntStatus(UART1_BASE, true); //get interrupt status
    UARTIntClear(UART1_BASE, ui32Status); //clear the asserted interrupts
    while(UARTCharsAvail(UART1_BASE)) //loop while there are chars
    {
        data = UARTCharGetNonBlocking(UART1_BASE);
        RINGBUF_Put(&UART0_RxRingBuff, data);
    }
}


void SysTick_Handler(void) //systick timer use for check flag and keep_alive message
{
    static uint32_t tick = 60;
    tick--;
    if(tick%3 == 0)
        flag.dht11  = true; // ngat la I, bat co dht11
    if (tick == 0)
        tick = 60;
}

//****************Timer 2 cound down connect to raspberry
void TIMER2A_Handler(void)
{
    TimerIntClear(TIMER2_BASE, TIMER_TIMA_TIMEOUT);
    GPIOPinWrite(GPIO_PORTF_BASE, GPIO_PIN_1,~GPIOPinRead(GPIO_PORTF_BASE,GPIO_PIN_1));
    uart_send_command(Address,array_connect,0x28,0xFF,0xFF); //send connect message
}

//****************Timer 0 cound down LED 1
void TIMER3A_Handler(void)
{
    TimerIntClear(TIMER3_BASE, TIMER_TIMA_TIMEOUT);
    timerLed1--;
    uart_send_command(Address,array_send,0x29,0x00,timerLed1);
    if (timerLed1 == 0)
    {
         GPIOPinWrite(GPIO_PORTF_BASE, GPIO_PIN_2, 0);
         uart_send_command(Address,array_send,0x21,0x00,0x00);
         flagLed1 = false;
         TimerDisable(TIMER3_BASE, TIMER_A);
    }

}
//****************Timer 1 cound down LED 2
void TIMER1A_Handler(void)
{
    TimerIntClear(TIMER1_BASE, TIMER_TIMA_TIMEOUT);
    timerLed2--;
    uart_send_command(Address,array_send,0x30,0x00,timerLed2);
    if (timerLed2 == 0)
        {
            GPIOPinWrite(GPIO_PORTF_BASE, GPIO_PIN_3, 0);
             uart_send_command(Address,array_send,0x22,0x00,0x00);
             flagLed2 = false;
             TimerDisable(TIMER1_BASE, TIMER_A);
        }
}

/*
void WDT0_Handler(void){ // Watchdog timer interrupt and reset MCU
    WatchdogIntClear(WATCHDOG0_BASE);
} */


/*******************State machine

1: get data from ring buff
2: check data and calculate CRC
3: CRC true, check byte in frame
*/
int uart_get(uint8_t *msg);
void check_frame(uint8_t *array);

int main(void)
{

    SysCtlClockSet(SYSCTL_SYSDIV_1 | SYSCTL_USE_PLL |
                   SYSCTL_OSC_MAIN | SYSCTL_XTAL_16MHZ); //setup clock 50Mhz
    // configure ringbufffer
    RINGBUF_Init(&UART0_RxRingBuff, buffer, SIZE);
    init_gpio();
    init_uart();
    init_timer();
    init_adc();
    SysTickPeriodSet(SysCtlClockGet()); //interrupt every 1s
    // interrupt priority
    IntPrioritySet(INT_UART1,   0x00);
    IntPrioritySet(INT_TIMER2A, 0x20);
    IntPrioritySet(INT_TIMER1A, 0x40);
    IntPrioritySet(INT_TIMER3A, 0x60);
    SysTickIntEnable();
    IntMasterEnable(); // enable global interrupt

    uint16_t crc_test; // crc check
    uint8_t array[20]; // array to store data which get get from ringbuffer

    uint32_t temp, humidity;
    uint16_t current;
    uint8_t currentHigh;
    uint8_t currentLow;
    while (1)
    {
            switch (state)
            {
                case CONNECT:
                    TimerEnable(TIMER2_BASE, TIMER_A); // wait 5s for timeout;
                    state = GETDATA;
                break;
                case GETDATA:
                    if (uart_get(array) == 1) // if receive '\n' end string, transfer to next state CHECKCRC
                    {
                        state = CHECKCRC;
                        break;
                    }
                    break;
                case CHECKCRC:
                    crc_test = crc_16(array,5);
                    if (crc_test != 0)
                    {//error receive
                        uart_send_command(Address,array_send,0x26,0xFF,0xFF);
                        memset (array,0,10);
                        state = GETDATA;
                        break;
                    }
                    else
                    { // receive success, crc_test=0
                        state = CHECKFRAME;
                        break;
                    }
                case CHECKFRAME:
                    check_frame(array);
                    memset (array,0,10);
                    state = GETDATA;
                    break;
            }
            if (on_connect)
                {
            // send data every 5s
               if( flag.dht11 == true)  // neu co bat. lau du lieu va gui ve raspberry
               {
                   ReadDHT(&temp, &humidity);
                   uart_send_command(Address,array_send,0x25,0x00,humidity);
                   SysCtlDelay(SysCtlClockGet()/30000);
                   uart_send_command(Address,array_send,0x24,0x00,temp);
                   flag.dht11 = false;
                   if (flagLed1 || flagLed2)
                   {
                       current = getAmpere();
                       if (current < 255)
                           uart_send_command(Address,array_send,0x23,0x00,current);
                       else
                       {
                           currentHigh = current >> 8;
                           currentLow = current;
                       uart_send_command(Address,array_send,0x23,currentHigh,currentLow);
                       }
                    }
               }
             }
    }
}
///////////////////////////////////////////////////////////////////
//
//FUNCTION -----------------------------
//
//
int uart_get(uint8_t *msg)
{
    uint8_t get;
    static uint16_t index = 0;
    while (RINGBUF_Get(&UART0_RxRingBuff, &get))
    {
        if (get == 0x0A)//receice end of string
        {
            index = 0;
            return 1;
        }
        else
        {
            *(msg+index) = get;
            index++;
        }
    }
    return 0;
}

void check_frame(uint8_t *array )
{
    uint8_t *ptr;
    ptr = array;
    //// check address and implement command
         if (*ptr == Address)  // kiem tra dia chi
         {
                 switch (*(ptr+1)) // kiem tra yeu cau
                 {
                 case 0x21: //led 1
                         if(*(ptr+2) == 0x11) //on led 1
                         {
                             flagLed1 = true;
                             GPIOPinWrite(GPIO_PORTF_BASE, GPIO_PIN_2, GPIO_PIN_2);
                             if (alarmLed1)
                             {
                                 alarmLed1 = false;
                                 TimerEnable(TIMER3_BASE, TIMER_A);
                             }
                             uart_send_command(Address,array_send,0x21,0x00,0x11); // gui cho raspberry biet da hoan tat
                         }
                         else if (*(ptr+2) == 0x00) //led off
                         {
                                 GPIOPinWrite(GPIO_PORTF_BASE, GPIO_PIN_2, 0);
                                 uart_send_command(Address,array_send,0x21,0x00,0x00);
                                 flagLed1 = false;
                                 TimerDisable(TIMER3_BASE, TIMER_A);
                         }
                         break;

                 case 0x22: //led 2
                         if(*(ptr+2) == 0x11) //on led 2
                         {
                                 flagLed2 = true;
                                 GPIOPinWrite(GPIO_PORTF_BASE, GPIO_PIN_3, GPIO_PIN_3);
                                 if (alarmLed2)
                                  {
                                      alarmLed2 = false;
                                      TimerEnable(TIMER1_BASE, TIMER_A);
                                  }
                                 uart_send_command(Address, array_send,0x22,0x00,0x11);
                         }
                         else if (*(ptr+2) == 0x00)//led off
                         {
                                 GPIOPinWrite(GPIO_PORTF_BASE, GPIO_PIN_3, 0);
                                 uart_send_command(Address,array_send,0x22,0x00,0x00);
                                 flagLed2 = false;
                                 TimerDisable(TIMER1_BASE, TIMER_A);
                         }
                         break;
                 case 0x27:
                     uart_send_command(Address,array_send,0x27,0xFF,0xFF);
                     break;
                 case 0x28:
                        on_connect = true;
                        TimerDisable(TIMER2_BASE, TIMER_A);
                        SysTickEnable();
                        GPIOPinWrite(GPIO_PORTF_BASE, GPIO_PIN_1,0);
                        //uart_send_string("connect success");
                        break;
                 case 0x29:
                     alarmLed1 = true;
                     timerLed1 = *(ptr+2);
                     uart_send_command(Address,array_send,0x29,0x00,timerLed1);
                     break;
                 case 0x30:
                     alarmLed2 = true;
                     timerLed2 = *(ptr+2);
                     uart_send_command(Address,array_send,0x30,0x00,timerLed2);
                     break;
                 }
         }
}




