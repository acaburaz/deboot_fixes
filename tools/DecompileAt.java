import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.util.task.ConsoleTaskMonitor;

public class DecompileAt extends GhidraScript {
    public void run() throws Exception {
        long[] targets = { 0x2abe0L, 0x2af8cL, 0x2aaf8L };
        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);
        FunctionManager fm = currentProgram.getFunctionManager();
        println("IMAGE_BASE=" + currentProgram.getImageBase());
        long base = currentProgram.getImageBase().getOffset();
        for (long a : targets) {
            Address addr = toAddr(base + a);
            Function fn = fm.getFunctionContaining(addr);
            println("\n// ===== target 0x" + Long.toHexString(a) + " =====");
            if (fn == null) { println("// (no function here)"); continue; }
            DecompileResults res = dec.decompileFunction(fn, 90, new ConsoleTaskMonitor());
            if (res == null || !res.decompileCompleted()) { println("// decompile failed: " + (res==null?"null":res.getErrorMessage())); continue; }
            println("// " + fn.getName() + " @ " + fn.getEntryPoint());
            println(res.getDecompiledFunction().getC());
        }
    }
}
