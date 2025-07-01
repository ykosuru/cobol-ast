import java.util.List;

class BusinessLogicResult {
    private List<CobolProcedure2> procedures;
    private List<StructuralDataItemV2> dataItems;
    private List<DataDivisionPreprocessor.FileDescriptor> fileDescriptors;
    
    public BusinessLogicResult(List<CobolProcedure2> procedures, 
                              List<StructuralDataItemV2> dataItems,
                              List<DataDivisionPreprocessor.FileDescriptor> fileDescriptors) {
        this.procedures = procedures;
        this.dataItems = dataItems;
        this.fileDescriptors = fileDescriptors;
    }
    
    public List<CobolProcedure2> getProcedures() { return procedures; }
    public List<StructuralDataItemV2> getDataItems() { return dataItems; }
    public List<DataDivisionPreprocessor.FileDescriptor> getFileDescriptors() { return fileDescriptors; }
}
