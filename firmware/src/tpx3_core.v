

`include "utils/bus_to_ip.v"
 
`include "gpio/gpio.v"

`include "spi/spi.v"
`include "spi/spi_core.v"
`include "spi/blk_mem_gen_8_to_1_2k.v"
`include "utils/cdc_pulse_sync.v"
`include "utils/CG_MOD_pos.v"

`include "utils/cdc_syncfifo.v"
`include "utils/generic_fifo.v"
`include "utils/cdc_reset_sync.v"

`include "bram_fifo/bram_fifo_core.v"
`include "bram_fifo/bram_fifo.v" 

`include "rrp_arbiter/rrp_arbiter.v" 

`include "../lib/tpx3_rx/tpx3_rx.v"
`include "../lib/tpx3_rx/tpx3_rx_core.v"
`include "../lib/tpx3_rx/receiver_logic.v"
`include "../lib/tpx3_rx/rec_sync.v"
`include "../lib/tpx3_rx/decode_8b10b.v"
`include "utils/flag_domain_crossing.v"


module tpx3_core (
    input wire          BUS_CLK,
    input wire          BUS_RST,
    input wire  [31:0]  BUS_ADD,
    inout wire   [31:0] BUS_DATA,
    input wire          BUS_RD,
    input wire          BUS_WR,
    output wire         BUS_BYTE_ACCESS,

    input wire CLK40, CLK32, CLK320,
    
    output wire ExtTPulse, 
    output wire T0_Sync, 
    output wire EnableIn, 
    output wire DataIn,  
    output wire Shutter, 
    output wire Reset, 
    output wire ENPowerPulsing,
    output wire Data_MUX_select,
    
    input wire [7:0] RX_DATA,
    
    output wire [7:0] LED,
    output wire RX_READY
    
    
);

    // MODULE ADREESSES //
    localparam GPIO_BASEADDR = 32'h1000;
    localparam GPIO_HIGHADDR = 32'h2000-1;
    
    localparam SPI_BASEADDR = 32'h2000; //0x1000
    localparam SPI_HIGHADDR = 32'h3000-1;   //0x300f
    
    localparam RX_BASEADDR = 16'h6000;
    localparam RX_HIGHADDR = 16'h7000-1; 
    
    localparam FIFO_BASEADDR = 32'h8000;
    localparam FIFO_HIGHADDR = 32'h9000-1;
    
    localparam FIFO_BASEADDR_DATA = 32'h8000_0000;
    localparam FIFO_HIGHADDR_DATA = 32'h9000_0000;
    
    localparam ABUSWIDTH = 32;
    assign BUS_BYTE_ACCESS = BUS_ADD < 32'h8000_0000 ? 1'b1 : 1'b0;
    

    /////////////
    // MODULES //
    /////////////
    wire [15:0] GPIO;
    gpio
    #(
        .BASEADDR(GPIO_BASEADDR),
        .HIGHADDR(GPIO_HIGHADDR),
        .ABUSWIDTH(ABUSWIDTH),
        .IO_WIDTH(16),
        .IO_DIRECTION(16'hffff)
    ) gpio
    (
        .BUS_CLK(BUS_CLK),
        .BUS_RST(BUS_RST),
        .BUS_ADD(BUS_ADD),
        .BUS_DATA(BUS_DATA[7:0]),
        .BUS_RD(BUS_RD),
        .BUS_WR(BUS_WR),
        .IO(GPIO)
    );
    
    assign Reset = GPIO[0];
    //assign EnableIn = GPIO[1];
    assign Shutter = GPIO[2];
    assign ExtTPulse = GPIO[3];
    assign T0_Sync = GPIO[4]; 
    assign ENPowerPulsing = GPIO[5];
    assign Data_MUX_select = GPIO[6];
    assign LED = GPIO[15:8];
    wire CNT_FIFO_EN;
    assign CNT_FIFO_EN = GPIO[7];
    
    wire SCLK, SDI, SDO, SEN, SLD;
    
    spi
    #(
        .BASEADDR(SPI_BASEADDR),
        .HIGHADDR(SPI_HIGHADDR),
        .ABUSWIDTH(ABUSWIDTH),
        .MEM_BYTES(1024) 
    )  spi
    (
        .BUS_CLK(BUS_CLK),
        .BUS_RST(BUS_RST),
        .BUS_ADD(BUS_ADD),
        .BUS_DATA(BUS_DATA[7:0]),
        .BUS_RD(BUS_RD),
        .BUS_WR(BUS_WR),
        
        .SPI_CLK(CLK40),
        .EXT_START(1'b0),
        
        .SCLK(SCLK),
        .SDI(SDI),
        .SDO(SDO),
        .SEN(SEN),
        .SLD(SLD)
    );
    assign DataIn = SDI;
    assign SDO = SDI;
    assign EnableIn = ~SEN;
    
    wire TPX_0_FIFO_READ;
    wire TPX_0_FIFO_EMPTY;
    wire [31:0] TPX_0_FIFO_DATA;

    tpx3_rx #(
        .BASEADDR(RX_BASEADDR),
        .HIGHADDR(RX_HIGHADDR),
        .DATA_IDENTIFIER(0),
        .ABUSWIDTH(ABUSWIDTH)
    ) tpx3_rx (
        
        .RX_CLKX2(CLK320),
        .RX_CLKW(CLK32),
        .RX_DATA(RX_DATA[0]),

        .RX_READY(RX_READY),
        .RX_8B10B_DECODER_ERR(),
        .RX_FIFO_OVERFLOW_ERR(),

        .FIFO_READ(TPX_0_FIFO_READ),
        .FIFO_EMPTY(TPX_0_FIFO_EMPTY),
        .FIFO_DATA(TPX_0_FIFO_DATA),

        .RX_FIFO_FULL(),
        .RX_ENABLED(),

        .BUS_CLK(BUS_CLK),
        .BUS_RST(BUS_RST),
        .BUS_ADD(BUS_ADD),
        .BUS_DATA(BUS_DATA[7:0]),
        .BUS_RD(BUS_RD),
        .BUS_WR(BUS_WR)
    );
    
    
    wire CNT_FIFO_READ;
    reg [31:0] CNT_FIFO_DATA;
    always@(posedge BUS_CLK)
        if(BUS_RST)
            CNT_FIFO_DATA <= 0;
        else if(CNT_FIFO_READ)
            CNT_FIFO_DATA <= CNT_FIFO_DATA + 1;
        
    wire ARB_READY_OUT, ARB_WRITE_OUT;
    wire [31:0] ARB_DATA_OUT;
    wire [1:0] READ_GRANT;

    rrp_arbiter #(
        .WIDTH(2)
    ) rrp_arbiter (
        .RST(BUS_RST),
        .CLK(BUS_CLK),

        .WRITE_REQ({~TPX_0_FIFO_EMPTY, CNT_FIFO_EN}),
        .HOLD_REQ({2'b0}),
        .DATA_IN({TPX_0_FIFO_DATA, CNT_FIFO_DATA}),
        .READ_GRANT(READ_GRANT),

        .READY_OUT(ARB_READY_OUT),
        .WRITE_OUT(ARB_WRITE_OUT),
        .DATA_OUT(ARB_DATA_OUT)
    );

    assign CNT_FIFO_READ = READ_GRANT[0];
    assign TPX_0_FIFO_READ = READ_GRANT[1];

    bram_fifo
    #(
        .BASEADDR(FIFO_BASEADDR),
        .HIGHADDR(FIFO_HIGHADDR),
        .BASEADDR_DATA(FIFO_BASEADDR_DATA),
        .HIGHADDR_DATA(FIFO_HIGHADDR_DATA),
        .ABUSWIDTH(ABUSWIDTH),
        .DEPTH(1024*32)
    ) out_fifo (
        .BUS_CLK(BUS_CLK),
        .BUS_RST(BUS_RST),
        .BUS_ADD(BUS_ADD),
        .BUS_DATA(BUS_DATA),
        .BUS_RD(BUS_RD),
        .BUS_WR(BUS_WR),

        .FIFO_READ_NEXT_OUT(ARB_READY_OUT),
        .FIFO_EMPTY_IN(~ARB_WRITE_OUT),
        .FIFO_DATA(ARB_DATA_OUT),

        .FIFO_NOT_EMPTY(),
        .FIFO_FULL(),
        .FIFO_NEAR_FULL(),
        .FIFO_READ_ERROR()
    );

    

endmodule
