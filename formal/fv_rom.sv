// Formal verification of format_rom -- SSOT catalog integrity.
// Proves: self-index, default-zero, non-zero, golden spot-checks.
`default_nettype none

module fv_rom (
    input wire clk
);
    (* anyconst *) reg [6:0] addr;
    wire [79:0] data;

    format_rom uut (.clk(clk), .addr(addr), .data(data));

    reg f_past_valid = 1'b0;
    always @(posedge clk) f_past_valid <= 1'b1;

    always @(posedge clk) if (f_past_valid) begin
        // P1: Self-index -- MSB byte of every record equals its address
        if (addr <= 7'd79) assert(data[79:72] == {1'b0, addr});

        // P2: Default zero for out-of-range addresses (80-127)
        if (addr > 7'd79) assert(data == 80'h0);

        // P3: Non-zero for all valid addresses
        if (addr <= 7'd79) assert(data != 80'h0);

        // P4: Golden spot-checks (first, middle, last record)
        if (addr == 7'd 0) assert(data == 80'h0007101050A01E370000);
        if (addr == 7'd40) assert(data == 80'h285706103025E1C81301);
        if (addr == 7'd79) assert(data == 80'h4F57081000759E371301);
    end
endmodule
