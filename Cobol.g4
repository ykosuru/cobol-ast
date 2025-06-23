/*
 * ANTLR based COBOL Grammar - Cobol.g4 
 * Designed to handle real-world COBOL source 
 * FIXES APPLIED:
 * 1. Fixed level number handling in data description entries
 * 2. Enhanced FD and WORKING-STORAGE section parsing
 * 3. Improved data description clause ordering
 * 4. Fixed EXEC SQL statement handling
 * 5. Better error recovery for malformed statements
 */

grammar Cobol;

/*
================================================================================
PARSER RULES
================================================================================
*/

// Main entry point
startRule : compilationUnit EOF ;

compilationUnit : programUnit+ ;

programUnit : identificationDivision
              environmentDivision?
              dataDivision?
              procedureDivision?
              nestedProgram*
              endProgramStatement? ;

nestedProgram : programUnit ;

endProgramStatement : END PROGRAM programName DOT ;

/*
================================================================================
IDENTIFICATION DIVISION - No changes needed
================================================================================
*/

identificationDivision : 
    (IDENTIFICATION | ID) DIVISION DOT
    programIdParagraph
    identificationDivisionBody* ;

programIdParagraph : 
    PROGRAM_ID DOT programName 
    (IS? (COMMON | INITIAL | LIBRARY | DEFINITION | RECURSIVE) PROGRAM?)? 
    DOT? ;

identificationDivisionBody : 
    authorParagraph | installationParagraph | dateWrittenParagraph | 
    dateCompiledParagraph | securityParagraph | remarksParagraph ;

authorParagraph : AUTHOR DOT commentEntry ;
installationParagraph : INSTALLATION DOT commentEntry ;
dateWrittenParagraph : DATE_WRITTEN DOT commentEntry ;
dateCompiledParagraph : DATE_COMPILED DOT commentEntry ;
securityParagraph : SECURITY DOT commentEntry ;
remarksParagraph : REMARKS DOT commentEntry ;

commentEntry : (~(AUTHOR | INSTALLATION | DATE_WRITTEN | DATE_COMPILED | 
                SECURITY | REMARKS | ENVIRONMENT | DATA | PROCEDURE | 
                DIVISION | EOF))* 
             | /* empty */ ;

/*
================================================================================
ENVIRONMENT DIVISION - No major changes needed
================================================================================
*/

environmentDivision : 
    ENVIRONMENT DIVISION DOT
    environmentDivisionBody* ;

environmentDivisionBody : 
    configurationSection | inputOutputSection ;

configurationSection : 
    CONFIGURATION SECTION DOT
    configurationSectionParagraph* ;

configurationSectionParagraph : 
    sourceComputerParagraph | objectComputerParagraph | 
    specialNamesParagraph | repositoryParagraph ;

sourceComputerParagraph : 
    SOURCE_COMPUTER DOT 
    (computerName (WITH? DEBUGGING MODE)? DOT)? ;

objectComputerParagraph : 
    OBJECT_COMPUTER DOT 
    (computerName objectComputerClause* DOT)? ;

objectComputerClause : 
    memorySizeClause | diskSizeClause | collatingSequenceClause | 
    segmentLimitClause | characterSetClause ;

memorySizeClause : 
    MEMORY SIZE? (integerLiteral | cobolWord) 
    (WORDS | CHARACTERS | MODULES)? ;

diskSizeClause : 
    DISK SIZE? IS? (integerLiteral | cobolWord) 
    (WORDS | MODULES)? ;

collatingSequenceClause : 
    PROGRAM? COLLATING? SEQUENCE (IS? alphabetName+) 
    collatingSequenceClauseAlphanumeric? 
    collatingSequenceClauseNational? ;

collatingSequenceClauseAlphanumeric : 
    FOR? ALPHANUMERIC IS? alphabetName ;

collatingSequenceClauseNational : 
    FOR? NATIONAL IS? alphabetName ;

segmentLimitClause : SEGMENT_LIMIT IS? integerLiteral ;

characterSetClause : CHARACTER SET DOT ;

repositoryParagraph : 
    REPOSITORY DOT repositoryEntry* DOT ;

repositoryEntry : 
    FUNCTION functionName (AS literal)? | 
    FUNCTION ALL INTRINSIC | 
    CLASS className (AS literal)? | 
    INTERFACE interfaceName (AS literal)? ;

specialNamesParagraph : 
    SPECIAL_NAMES DOT 
    (specialNameClause+ DOT)? ;

specialNameClause : 
    channelClause | odtClause | alphabetClause | classClause | 
    currencySignClause | decimalPointClause | symbolicCharactersClause | 
    environmentSwitchNameClause | defaultDisplaySignClause | 
    defaultComputationalSignClause | reserveNetworkClause ;

alphabetClause : 
    ALPHABET alphabetName (FOR ALPHANUMERIC)? IS? 
    (EBCDIC | ASCII | STANDARD_1 | STANDARD_2 | NATIVE | 
     cobolWord | alphabetLiterals+) ;

alphabetLiterals : literal (alphabetThrough | alphabetAlso+)? ;
alphabetThrough : (THROUGH | THRU) literal ;
alphabetAlso : ALSO literal+ ;

channelClause : CHANNEL integerLiteral IS? mnemonicName ;

classClause : 
    CLASS className (FOR? (ALPHANUMERIC | NATIONAL))? IS? 
    classClauseThrough+ ;

classClauseThrough : 
    classClauseFrom ((THROUGH | THRU) classClauseTo)? ;

classClauseFrom : identifier | literal ;
classClauseTo : identifier | literal ;

currencySignClause : 
    CURRENCY SIGN? IS? literal 
    (WITH? PICTURE SYMBOL literal)? ;

decimalPointClause : DECIMAL_POINT IS? COMMA ;

defaultComputationalSignClause : 
    DEFAULT (COMPUTATIONAL | COMP)? (SIGN IS?)? 
    (LEADING | TRAILING)? (SEPARATE CHARACTER?) ;

defaultDisplaySignClause : 
    DEFAULT_DISPLAY (SIGN IS?)? (LEADING | TRAILING) 
    (SEPARATE CHARACTER?)? ;

environmentSwitchNameClause : 
    environmentName IS? mnemonicName 
    environmentSwitchNameSpecialNamesStatusPhrase? |
    environmentSwitchNameSpecialNamesStatusPhrase ;

environmentSwitchNameSpecialNamesStatusPhrase : 
    ON STATUS? IS? condition (OFF STATUS? IS? condition)? |
    OFF STATUS? IS? condition (ON STATUS? IS? condition)? ;

odtClause : ODT IS? mnemonicName ;

reserveNetworkClause : 
    RESERVE WORDS? LIST? IS? NETWORK CAPABLE? ;

symbolicCharactersClause : 
    SYMBOLIC CHARACTERS? (FOR? (ALPHANUMERIC | NATIONAL))? 
    symbolicCharacters+ (IN alphabetName)? ;

symbolicCharacters : 
    symbolicCharacter+ (IS | ARE)? integerLiteral+ ;

/*
================================================================================
INPUT-OUTPUT SECTION
================================================================================
*/

inputOutputSection : 
    INPUT_OUTPUT SECTION DOT
    inputOutputSectionParagraph* ;

inputOutputSectionParagraph : 
    fileControlParagraph | ioControlParagraph ;

fileControlParagraph : 
    FILE_CONTROL DOT fileControlEntry* ;

fileControlEntry : 
    selectClause fileControlClause* DOT ;

selectClause : SELECT OPTIONAL? fileName ;

fileControlClause : 
    assignClause | reserveClause | organizationClause | 
    paddingCharacterClause | recordDelimiterClause | accessModeClause | 
    recordKeyClause | alternateRecordKeyClause | fileStatusClause | 
    passwordClause | relativeKeyClause | sharingClause | lockModeClause ;

// Fixed assign clause to handle various formats
assignClause : 
    ASSIGN TO? assignTarget ;

assignTarget : 
    (DISK | DISPLAY | KEYBOARD | PORT | PRINTER | READER | REMOTE | 
     TAPE | VIRTUAL | (DYNAMIC | EXTERNAL)? assignmentName | 
     literal | cobolWord) ;

reserveClause : 
    RESERVE (NO | integerLiteral) ALTERNATE? (AREA | AREAS)? ;

organizationClause : 
    (ORGANIZATION IS?)? 
    (LINE | RECORD BINARY | RECORD | BINARY)? 
    (SEQUENTIAL | RELATIVE | INDEXED) ;

paddingCharacterClause : 
    PADDING CHARACTER? IS? (qualifiedDataName | literal) ;

recordDelimiterClause : 
    RECORD DELIMITER IS? (STANDARD_1 | IMPLICIT | assignmentName) ;

accessModeClause : 
    ACCESS MODE? IS? (SEQUENTIAL | RANDOM | DYNAMIC | EXCLUSIVE) ;

recordKeyClause : 
    RECORD KEY? IS? qualifiedDataName passwordClause? 
    (WITH? DUPLICATES)? ;

alternateRecordKeyClause : 
    ALTERNATE RECORD KEY? IS? qualifiedDataName passwordClause? 
    (WITH? DUPLICATES)? ;

passwordClause : PASSWORD IS? dataName ;

// Enhanced file status clause to handle the parsing issue
fileStatusClause : 
    (FILE? (STATUS | STAT) IS? qualifiedDataName qualifiedDataName?) |
    ((STATUS | STAT) IS? qualifiedDataName qualifiedDataName?) ;

relativeKeyClause : RELATIVE KEY? IS? qualifiedDataName ;

sharingClause : 
    SHARING WITH? (ALL OTHER | NO OTHER | READ ONLY) ;

lockModeClause : 
    LOCK MODE IS? (MANUAL | AUTOMATIC | EXCLUSIVE) ;

ioControlParagraph : 
    I_O_CONTROL DOT (fileName DOT)? 
    (ioControlClause* DOT)? ;

ioControlClause : 
    rerunClause | sameClause | multipleFileClause | 
    commitmentControlClause ;

rerunClause : 
    RERUN (ON (assignmentName | fileName))? EVERY 
    (rerunEveryRecords | rerunEveryOf | rerunEveryClock) ;

rerunEveryRecords : integerLiteral RECORDS ;
rerunEveryOf : END? OF? (REEL | UNIT) OF fileName ;
rerunEveryClock : integerLiteral CLOCK_UNITS? ;

sameClause : 
    SAME (RECORD | SORT | SORT_MERGE)? AREA? FOR? fileName+ ;

multipleFileClause : 
    MULTIPLE FILE TAPE? CONTAINS? multipleFilePosition+ ;

multipleFilePosition : 
    fileName (POSITION integerLiteral)? ;

commitmentControlClause : COMMITMENT CONTROL FOR? fileName ;

/*
================================================================================
DATA DIVISION - CRITICAL FIX
================================================================================
*/

dataDivision
    : DATA DIVISION DOT dataDivisionSection*
    ;

// CRITICAL FIX: Each section must be completely independent with clear section headers
dataDivisionSection : 
    (FILE SECTION DOT fileDescriptionEntry*) |
    (WORKING_STORAGE SECTION DOT dataDescriptionEntry*) |
    (LINKAGE SECTION DOT dataDescriptionEntry*) |
    (COMMUNICATION SECTION DOT communicationDescriptionEntry*) |
    (LOCAL_STORAGE SECTION DOT dataDescriptionEntry*) |
    (SCREEN SECTION DOT screenDescriptionEntry*) |
    (REPORT SECTION DOT reportDescription*) |
    (PROGRAM_LIBRARY SECTION DOT libraryDescriptionEntry*) |
    (DATA_BASE SECTION DOT dataBaseSectionEntry*) ;

// FIXED: FD entries with proper structure
fileDescriptionEntry
    : FD fileName fileDescriptionClause* DOT dataDescriptionEntry*
    ;



/*
================================================================================
DATA DESCRIPTION ENTRIES - COMPLETELY FIXED
================================================================================
*/

dataDescriptionEntry : 
    dataDescriptionEntryLevel01 | 
    dataDescriptionEntryLevel02_49 |
    dataDescriptionEntryLevel66 | 
    dataDescriptionEntryLevel77 | 
    dataDescriptionEntryLevel88 | 
    dataDescriptionEntryExecSql | 
    copyStatement ;

// FIXED: Separate rules for each level type to avoid conflicts
dataDescriptionEntryLevel01 : 
    LEVEL_NUMBER_01 (FILLER | dataName)? dataDescriptionClause* DOT ;

dataDescriptionEntryLevel02_49 : 
    LEVEL_NUMBER_02_49 (FILLER | dataName)? dataDescriptionClause* DOT ;

dataDescriptionEntryLevel66 : 
    LEVEL_NUMBER_66 dataName dataRenamesClause DOT ;

dataDescriptionEntryLevel77 : 
    LEVEL_NUMBER_77 dataName dataDescriptionClause* DOT ;

dataDescriptionEntryLevel88 : 
    LEVEL_NUMBER_88 conditionName dataValueClause DOT ;

// EXEC SQL INCLUDE - FIXED
dataDescriptionEntryExecSql : 
    EXEC SQL INCLUDE cobolWord END_EXEC DOT? ;

/*
================================================================================
FILE DESCRIPTION CLAUSE DEFINITIONS  
================================================================================
*/

externalClause : IS? EXTERNAL ;

globalClause : IS? GLOBAL ;

blockContainsClause
    : BLOCK CONTAINS (INTEGERLITERAL | NUMERICLITERAL) (TO (INTEGERLITERAL | NUMERICLITERAL))? 
      (CHARACTERS | RECORDS)?
    ;

recordContainsClause : 
    RECORD (recordContainsClauseFormat1 | 
            recordContainsClauseFormat2 | 
            recordContainsClauseFormat3) ;

recordContainsClauseFormat1 : 
    CONTAINS? integerLiteral CHARACTERS? ;

recordContainsClauseFormat2 : 
    IS? VARYING IN? SIZE? 
    (FROM? integerLiteral recordContainsTo? CHARACTERS?)? 
    (DEPENDING ON? qualifiedDataName)? ;

recordContainsClauseFormat3 : 
    CONTAINS? integerLiteral recordContainsTo CHARACTERS? ;

recordContainsTo : TO integerLiteral ;

labelRecordsClause
    : LABEL (RECORD IS | RECORDS ARE) (STANDARD | OMITTED | dataName)
    ;

valueOfClause : VALUE OF valuePair+ ;

valuePair : systemName IS? (qualifiedDataName | literal) ;

dataRecordsClause
    : DATA (RECORD IS | RECORDS ARE) dataName+
    ;

recordingModeClause
    : RECORDING MODE IS (RECORDING_MODE_F | RECORDING_MODE_V | RECORDING_MODE_U | RECORDING_MODE_S)
    ;

linageClause : 
    LINAGE IS? (dataName | integerLiteral) LINES? linageAt* ;

linageAt : 
    linageFootingAt | linageLinesAtTop | linageLinesAtBottom ;

linageFootingAt : 
    WITH? FOOTING AT? (dataName | integerLiteral) ;

linageLinesAtTop : 
    LINES? AT? TOP (dataName | integerLiteral) ;

linageLinesAtBottom : 
    LINES? AT? BOTTOM (dataName | integerLiteral) ;

codeSetClause : CODE_SET IS? alphabetName ;

reportClause : (REPORT IS? | REPORTS ARE?) reportName+ ;

// FIXED: Proper file description clauses 
fileDescriptionClause : 
    externalClause | globalClause | blockContainsClause | 
    recordContainsClause | labelRecordsClause | valueOfClause | 
    dataRecordsClause | linageClause | codeSetClause | 
    reportClause | recordingModeClause ;

dataDescriptionClause : 
    dataRedefinesClause | dataPictureClause | dataUsageClause | 
    dataIntegerStringClause | dataExternalClause | 
    dataGlobalClause | dataTypeDefClause | dataThreadLocalClause | 
    dataCommonOwnLocalClause | dataTypeClause | 
    dataUsingClause | dataReceivedByClause | 
    dataOccursClause | dataSignClause | dataSynchronizedClause | 
    dataJustifiedClause | dataBlankWhenZeroClause | dataWithLowerBoundsClause | 
    dataAlignedClause | dataRecordAreaClause | dataVolatileClause | 
    dataBasedClause | dataValueClause ;

dataRedefinesClause : REDEFINES dataName ;

// FIXED: Enhanced Java type support  
dataIntegerStringClause 
    : INTEGER | STRING | SHORT | INT | JAVA_LONG | JAVA_DOUBLE | JAVA_FLOAT | 
      JAVA_BOOLEAN | JAVA_BYTE | JAVA_CHAR | JAVA_BIG_DECIMAL
    ;

dataExternalClause : IS? EXTERNAL (BY literal)? ;
dataGlobalClause : IS? GLOBAL ;
dataTypeDefClause : IS? TYPEDEF ;
dataThreadLocalClause : IS? THREAD_LOCAL ;

dataPictureClause : (PICTURE | PIC) IS? pictureString ;

pictureString : PICTURE_STRING | STRING | SHORT | INT ;

// FIXED: Enhanced usage clause with Java types
dataUsageClause : 
    (USAGE IS?)? 
    (BINARY (TRUNCATED | EXTENDED)? | 
     BIT | 
     COMP | 
     COMP_1 | 
     COMP_2 | 
     COMP_3 | 
     COMP_4 | 
     COMP_5 | 
     COMP_6 | 
     COMPUTATIONAL | 
     COMPUTATIONAL_1 | 
     COMPUTATIONAL_2 | 
     COMPUTATIONAL_3 | 
     COMPUTATIONAL_4 | 
     COMPUTATIONAL_5 | 
     COMPUTATIONAL_6 | 
     CONTROL_POINT | 
     DATE | 
     DISPLAY | 
     DISPLAY_1 | 
     DOUBLE | 
     EVENT | 
     FLOAT_BINARY_32 | 
     FLOAT_BINARY_64 | 
     FLOAT_DECIMAL_16 | 
     FLOAT_DECIMAL_34 | 
     FLOAT_EXTENDED | 
     FUNCTION_POINTER | 
     INDEX | 
     KANJI | 
     LOCK | 
     NATIONAL | 
     PACKED_DECIMAL | 
     POINTER | 
     PROCEDURE_POINTER | 
     REAL | 
     SQL | 
     TASK | 
     OBJECT_REFERENCE className? | 
     UTF_8 | 
     UTF_16 |
     STRING |
     SHORT |
     INT |
     JAVA_LONG |
     JAVA_DOUBLE |
     JAVA_FLOAT |
     JAVA_BOOLEAN |
     JAVA_BYTE |
     JAVA_CHAR |
     JAVA_BIG_DECIMAL);

dataCommonOwnLocalClause : COMMON | OWN | LOCAL ;

dataTypeClause : 
    TYPE IS? (SHORT_DATE | LONG_DATE | NUMERIC_DATE | NUMERIC_TIME | 
              LONG_TIME | TIMESTAMP | TIMESTAMP_WITH_TIMEZONE | 
              (CLOB | BLOB | DBCLOB) LPARENCHAR integerLiteral RPARENCHAR) ;

dataUsingClause : 
    USING (LANGUAGE | CONVENTION) OF? (cobolWord | dataName) ;

dataValueClause : (VALUE | VL) (IS | ARE)? dataValueInterval ;

dataValueInterval : 
    dataValueIntervalFrom dataValueIntervalTo? ;

dataValueIntervalFrom : 
    literal | cobolWord | figurativeConstant ;

dataValueIntervalTo : (THROUGH | THRU) literal ;

dataReceivedByClause : 
    RECEIVED? BY? (CONTENT | REFERENCE | REF) ;

dataOccursClause : 
    OCCURS (identifier | integerLiteral) dataOccursTo? TIMES? 
    dataOccursDepending? (dataOccursSort | dataOccursIndexed)* ;

dataOccursTo : TO integerLiteral ;

dataOccursDepending : DEPENDING ON? qualifiedDataName ;

dataOccursSort : 
    (ASCENDING | DESCENDING) KEY? IS? qualifiedDataName+ ;

dataOccursIndexed : INDEXED BY? LOCAL? indexName+ ;

dataSignClause : (SIGN IS?)? (LEADING | TRAILING) (SEPARATE CHARACTER?)? ;

dataSynchronizedClause : 
    (SYNCHRONIZED | SYNC) (LEFT | RIGHT)? ;

dataJustifiedClause : (JUSTIFIED | JUST) RIGHT? ;

dataBlankWhenZeroClause : 
    BLANK WHEN? (ZERO | ZEROS | ZEROES) ;

dataWithLowerBoundsClause : WITH? LOWER BOUNDS ;

dataAlignedClause : ALIGNED ;

dataRecordAreaClause : RECORD AREA ;

dataVolatileClause : VOLATILE ;

dataBasedClause : BASED ON? qualifiedDataName ;

dataRenamesClause : 
    RENAMES qualifiedDataName 
    ((THROUGH | THRU) qualifiedDataName)? ;

/*
================================================================================
OTHER SECTIONS
================================================================================
*/

dataBaseSection : 
    DATA_BASE SECTION DOT dataBaseSectionEntry* ;

dataBaseSectionEntry : 
    integerLiteral literal INVOKE literal ;

linkageSection : 
    LINKAGE SECTION DOT dataDescriptionEntry* ;

communicationSection : 
    COMMUNICATION SECTION DOT communicationDescriptionEntry* ;

communicationDescriptionEntry : 
    CD cdName (FOR? (INITIAL? INPUT | OUTPUT | INITIAL I_O))? 
    communicationClause* DOT dataDescriptionEntry* ;

communicationClause : 
    symbolicQueueClause | symbolicSubQueueClause | messageDateClause | 
    messageTimeClause | symbolicSourceClause | textLengthClause | 
    endKeyClause | statusKeyClause | messageCountClause ;

symbolicQueueClause : SYMBOLIC? QUEUE IS? dataDescName ;
symbolicSubQueueClause : 
    SYMBOLIC? (SUB_QUEUE_1 | SUB_QUEUE_2 | SUB_QUEUE_3) IS? dataDescName ;
messageDateClause : MESSAGE DATE IS? dataDescName ;
messageTimeClause : MESSAGE TIME IS? dataDescName ;
symbolicSourceClause : SYMBOLIC? SOURCE IS? dataDescName ;
textLengthClause : TEXT LENGTH IS? dataDescName ;
endKeyClause : END KEY IS? dataDescName ;
statusKeyClause : STATUS KEY IS? dataDescName ;
messageCountClause : MESSAGE? COUNT IS? dataDescName ;

localStorageSection : 
    LOCAL_STORAGE SECTION DOT 
    (LD localName DOT)? dataDescriptionEntry* ;

screenSection : 
    SCREEN SECTION DOT screenDescriptionEntry* ;

screenDescriptionEntry : 
    levelNumber (FILLER | screenName)? 
    screenDescriptionClause* DOT ;

screenDescriptionClause : 
    screenDescriptionBlankClause | screenDescriptionBellClause | 
    screenDescriptionBlinkClause | screenDescriptionEraseClause | 
    screenDescriptionLightClause | screenDescriptionGridClause | 
    screenDescriptionReverseVideoClause | screenDescriptionUnderlineClause | 
    screenDescriptionSizeClause | screenDescriptionLineClause | 
    screenDescriptionColumnClause | screenDescriptionForegroundColorClause | 
    screenDescriptionBackgroundColorClause | screenDescriptionControlClause | 
    screenDescriptionValueClause | screenDescriptionPictureClause | 
    (screenDescriptionFromClause | screenDescriptionUsingClause) | 
    screenDescriptionUsageClause | screenDescriptionBlankWhenZeroClause | 
    screenDescriptionJustifiedClause | screenDescriptionSignClause | 
    screenDescriptionAutoClause | screenDescriptionSecureClause | 
    screenDescriptionRequiredClause | screenDescriptionPromptClause | 
    screenDescriptionFullClause | screenDescriptionZeroFillClause ;

screenDescriptionBlankClause : BLANK (SCREEN | LINE) ;
screenDescriptionBellClause : BELL | BEEP ;
screenDescriptionBlinkClause : BLINK ;
screenDescriptionEraseClause : ERASE (EOL | EOS) ;
screenDescriptionLightClause : HIGHLIGHT | LOWLIGHT ;
screenDescriptionGridClause : GRID | LEFTLINE | OVERLINE ;
screenDescriptionReverseVideoClause : REVERSE_VIDEO ;
screenDescriptionUnderlineClause : UNDERLINE ;
screenDescriptionSizeClause : SIZE IS? (identifier | integerLiteral) ;
screenDescriptionLineClause : 
    LINE (NUMBER? IS? (PLUS | PLUSCHAR | MINUSCHAR))? 
    (identifier | integerLiteral) ;
screenDescriptionColumnClause : 
    (COLUMN | COL) (NUMBER? IS? (PLUS | PLUSCHAR | MINUSCHAR))? 
    (identifier | integerLiteral) ;
screenDescriptionForegroundColorClause : 
    (FOREGROUND_COLOR | FOREGROUND_COLOUR) IS? 
    (identifier | integerLiteral) ;
screenDescriptionBackgroundColorClause : 
    (BACKGROUND_COLOR | BACKGROUND_COLOUR) IS? 
    (identifier | integerLiteral) ;
screenDescriptionControlClause : CONTROL IS? identifier ;
screenDescriptionValueClause : (VALUE IS?) literal ;
screenDescriptionPictureClause : (PICTURE | PIC) IS? pictureString ;
screenDescriptionFromClause : 
    FROM (identifier | literal) screenDescriptionToClause? ;
screenDescriptionToClause : TO identifier ;
screenDescriptionUsingClause : USING identifier ;
screenDescriptionUsageClause : (USAGE IS?) (DISPLAY | DISPLAY_1) ;
screenDescriptionBlankWhenZeroClause : BLANK WHEN? ZERO ;
screenDescriptionJustifiedClause : (JUSTIFIED | JUST) RIGHT? ;
screenDescriptionSignClause : 
    (SIGN IS?)? (LEADING | TRAILING) (SEPARATE CHARACTER?)? ;
screenDescriptionAutoClause : AUTO | AUTO_SKIP ;
screenDescriptionSecureClause : SECURE | NO_ECHO ;
screenDescriptionRequiredClause : REQUIRED | EMPTY_CHECK ;
screenDescriptionPromptClause : 
    PROMPT CHARACTER? IS? (identifier | literal) 
    screenDescriptionPromptOccursClause? ;
screenDescriptionPromptOccursClause : 
    OCCURS integerLiteral TIMES? ;
screenDescriptionFullClause : FULL | LENGTH_CHECK ;
screenDescriptionZeroFillClause : ZERO_FILL ;

reportSection : 
    REPORT SECTION DOT reportDescription* ;

reportDescription : 
    reportDescriptionEntry reportGroupDescriptionEntry+ ;

reportDescriptionEntry : 
    RD reportName reportDescriptionGlobalClause? 
    (reportDescriptionPageLimitClause reportDescriptionHeadingClause? 
     reportDescriptionFirstDetailClause? reportDescriptionLastDetailClause? 
     reportDescriptionFootingClause?)? DOT ;

reportDescriptionGlobalClause : IS? GLOBAL ;
reportDescriptionPageLimitClause : 
    PAGE (LIMIT IS? | LIMITS ARE?)? integerLiteral (LINE | LINES)? ;
reportDescriptionHeadingClause : HEADING integerLiteral ;
reportDescriptionFirstDetailClause : FIRST DETAIL integerLiteral ;
reportDescriptionLastDetailClause : LAST DETAIL integerLiteral ;
reportDescriptionFootingClause : FOOTING integerLiteral ;

reportGroupDescriptionEntry : 
    reportGroupDescriptionEntryFormat1 | 
    reportGroupDescriptionEntryFormat2 | 
    reportGroupDescriptionEntryFormat3 ;

reportGroupDescriptionEntryFormat1 : 
    levelNumber dataName reportGroupLineNumberClause? 
    reportGroupNextGroupClause? reportGroupTypeClause 
    reportGroupUsageClause? DOT ;

reportGroupDescriptionEntryFormat2 : 
    levelNumber dataName? reportGroupLineNumberClause? 
    reportGroupUsageClause DOT ;

reportGroupDescriptionEntryFormat3 : 
    levelNumber dataName? reportGroupClause* DOT ;

reportGroupClause : 
    reportGroupPictureClause | reportGroupUsageClause | 
    reportGroupSignClause | reportGroupJustifiedClause | 
    reportGroupBlankWhenZeroClause | reportGroupLineNumberClause | 
    reportGroupColumnNumberClause | 
    (reportGroupSourceClause | reportGroupValueClause | 
     reportGroupSumClause | reportGroupResetClause) | 
    reportGroupIndicateClause ;

reportGroupPictureClause : (PICTURE | PIC) IS? pictureString ;
reportGroupUsageClause : (USAGE IS?)? (DISPLAY | DISPLAY_1) ;
reportGroupSignClause : 
    SIGN IS? (LEADING | TRAILING) SEPARATE CHARACTER? ;
reportGroupJustifiedClause : (JUSTIFIED | JUST) RIGHT? ;
reportGroupBlankWhenZeroClause : BLANK WHEN? ZERO ;
reportGroupLineNumberClause : 
    LINE? NUMBER? IS? 
    (reportGroupLineNumberNextPage | reportGroupLineNumberPlus) ;
reportGroupLineNumberNextPage : 
    integerLiteral (ON? NEXT PAGE)? ;
reportGroupLineNumberPlus : PLUS integerLiteral ;
reportGroupColumnNumberClause : 
    COLUMN NUMBER? IS? integerLiteral ;
reportGroupSourceClause : SOURCE IS? identifier ;
reportGroupValueClause : VALUE IS? literal ;
reportGroupSumClause : 
    SUM identifier (COMMA_CHAR? identifier)* 
    (UPON dataName (COMMA_CHAR? dataName)*)? ;
reportGroupResetClause : RESET ON? (FINAL | dataName) ;
reportGroupIndicateClause : GROUP INDICATE? ;
reportGroupNextGroupClause : 
    NEXT GROUP IS? (integerLiteral | reportGroupNextGroupNextPage | 
                    reportGroupNextGroupPlus) ;
reportGroupNextGroupNextPage : NEXT PAGE ;
reportGroupNextGroupPlus : PLUS integerLiteral ;
reportGroupTypeClause : 
    TYPE IS? (reportGroupTypeReportHeading | reportGroupTypePageHeading | 
              reportGroupTypeControlHeading | reportGroupTypeDetail | 
              reportGroupTypeControlFooting | reportGroupTypePageFooting | 
              reportGroupTypeReportFooting) ;
reportGroupTypeReportHeading : REPORT HEADING | RH ;
reportGroupTypePageHeading : PAGE HEADING | PH ;
reportGroupTypeControlHeading : 
    (CONTROL HEADING | CH) (FINAL | dataName) ;
reportGroupTypeDetail : DETAIL | DE ;
reportGroupTypeControlFooting : 
    (CONTROL FOOTING | CF) (FINAL | dataName) ;
reportGroupTypePageFooting : PAGE FOOTING | PF ;
reportGroupTypeReportFooting : REPORT FOOTING | RF ;

programLibrarySection : 
    PROGRAM_LIBRARY SECTION DOT libraryDescriptionEntry* ;

libraryDescriptionEntry : 
    libraryDescriptionEntryFormat1 | libraryDescriptionEntryFormat2 ;

libraryDescriptionEntryFormat1 : 
    LD libraryName EXPORT libraryAttributeClauseFormat1? 
    libraryEntryProcedureClauseFormat1? ;

libraryDescriptionEntryFormat2 : 
    LB libraryName IMPORT libraryIsGlobalClause? 
    libraryIsCommonClause? 
    (libraryAttributeClauseFormat2 | 
     libraryEntryProcedureClauseFormat2)* ;

libraryAttributeClauseFormat1 : 
    ATTRIBUTE (SHARING IS? 
               (DONTCARE | PRIVATE | SHAREDBYRUNUNIT | SHAREDBYALL))? ;

libraryAttributeClauseFormat2 : 
    ATTRIBUTE libraryAttributeFunction? 
    (LIBACCESS IS? (BYFUNCTION | BYTITLE))? 
    libraryAttributeParameter? libraryAttributeTitle? ;

libraryAttributeFunction : FUNCTIONNAME IS literal ;
libraryAttributeParameter : LIBPARAMETER IS? literal ;
libraryAttributeTitle : TITLE IS? literal ;

libraryEntryProcedureClauseFormat1 : 
    ENTRY_PROCEDURE programName libraryEntryProcedureForClause? ;

libraryEntryProcedureClauseFormat2 : 
    ENTRY_PROCEDURE programName libraryEntryProcedureForClause? 
    libraryEntryProcedureWithClause? libraryEntryProcedureUsingClause? 
    libraryEntryProcedureGivingClause? ;

libraryEntryProcedureForClause : FOR literal ;
libraryEntryProcedureGivingClause : GIVING dataName ;
libraryEntryProcedureUsingClause : 
    USING libraryEntryProcedureUsingName+ ;
libraryEntryProcedureUsingName : dataName | fileName ;
libraryEntryProcedureWithClause : 
    WITH libraryEntryProcedureWithName+ ;
libraryEntryProcedureWithName : localName | fileName ;
libraryIsCommonClause : IS? COMMON ;
libraryIsGlobalClause : IS? GLOBAL ;

/*
================================================================================
COPY STATEMENT
================================================================================
*/

copyStatement : 
    COPY copyName (OF | IN)? libraryName? 
    (REPLACING copyReplacingPhrase)? DOT ;

copyName : literal | cobolWord ;

copyReplacingPhrase : copyReplacingOperand+ ;

copyReplacingOperand : 
    (LEADING | TRAILING)? copyReplacingItem BY copyReplacingItem ;

copyReplacingItem : literal | cobolWord | pseudoText ;

pseudoText : 
    PSEUDO_TEXT_DELIMITER pseudoTextContent* PSEUDO_TEXT_DELIMITER ;

pseudoTextContent : ~(PSEUDO_TEXT_DELIMITER)+ ;

/*
================================================================================
PROCEDURE DIVISION - ENHANCED
================================================================================
*/

procedureDivision : 
    PROCEDURE DIVISION procedureDivisionUsingClause? 
    procedureDivisionGivingClause? DOT 
    procedureDeclaratives? procedureDivisionBody ;

procedureDeclaratives : 
    DECLARATIVES DOT procedureDeclarative+ END DECLARATIVES DOT ;

procedureDeclarative : 
    procedureSectionHeader DOT useStatement DOT paragraphs ;

procedureSectionHeader : sectionName (SECTION integerLiteral?)? ; // Allow implicit sections

procedureSection : procedureSectionHeader DOT (paragraphs | sentence)+ ;

procedureDivisionBody : (procedureSection | paragraph | statement | customTerminator | skipNumericName)* ;

skipNumericName : integerLiteral ; // Log as warning in listener

customTerminator : EXIT | GOBACK | STOP RUN | END PROGRAM ; // Dialect-specific terminators

procedureDivisionUsingClause : 
    (USING | CHAINING) procedureDivisionUsingParameter+ ;

procedureDivisionUsingParameter : 
    procedureDivisionByReferencePhrase | procedureDivisionByValuePhrase ;

procedureDivisionByReferencePhrase : 
    (BY? REFERENCE)? procedureDivisionByReference+ ;

procedureDivisionByReference : 
    (OPTIONAL? (identifier | fileName)) | ANY ;

procedureDivisionByValuePhrase : 
    BY? VALUE procedureDivisionByValue+ ;

procedureDivisionByValue : identifier | literal | ANY ;

procedureDivisionGivingClause : 
    GIVING (identifier | qualifiedDataName) ;

paragraphs : paragraph+ ;

paragraph : paragraphName DOT sentence* ;

sentence : statement+ DOT ;

/*
================================================================================
STATEMENTS - ENHANCED EXEC SQL HANDLING
================================================================================
*/

statement : 
    acceptStatement | addStatement | alterStatement | allocateStatement | 
    callStatement | cancelStatement | closeStatement | computeStatement | 
    continueStatement | deleteStatement | disableStatement | 
    displayStatement | divideStatement | enableStatement | entryStatement | 
    evaluateStatement | exhibitStatement | execCicsStatement | 
    execSqlStatement | execSqlImsStatement | exitStatement | 
    freeStatement | generateStatement | gobackStatement | goToStatement | 
    ifStatement | initializeStatement | initiateStatement | 
    inspectStatement | invokeStatement | jsonGenerateStatement | 
    jsonParseStatement | mergeStatement | moveStatement | 
    multiplyStatement | nextSentenceStatement | openStatement | 
    performStatement | purgeStatement | raiseStatement | readStatement | 
    receiveStatement | releaseStatement | resumeStatement | 
    returnStatement | rewriteStatement | searchStatement | sendStatement | 
    setStatement | sortStatement | startStatement | stopStatement | 
    stringStatement | subtractStatement | terminateStatement | 
    unstringStatement | writeStatement | xmlGenerateStatement | 
    xmlParseStatement | execStatement | simpleStatement ;

// FIXED: Enhanced EXEC SQL statement handling
execSqlStatement 
    : EXEC SQL sqlStatementBody? END_EXEC DOT?
    ;

sqlStatementBody
    : sqlToken+  
    ;

sqlToken
    : ~(END_EXEC | DOT)  // Any token except END_EXEC or DOT
    ;

execStatement : EXEC (SQL | CICS | IDENTIFIER) (~END_EXEC)* END_EXEC ;

simpleStatement : (ACCEPT | ADD | ALTER | CALL | COMPUTE | DISPLAY | MOVE | PERFORM | STOP | IF | EXEC) (IDENTIFIER | literal | DOT)* DOT? ;


// Key statements for COBOL processing
acceptStatement : 
    ACCEPT identifier (acceptFromDateStatement | acceptFromEscapeKeyStatement | 
                      acceptFromMnemonicStatement | acceptMessageCountStatement)? 
    onExceptionClause? notOnExceptionClause? END_ACCEPT? ;

acceptFromDateStatement : 
    FROM (DATE YYYYMMDD? | DAY YYYYDDD? | DAY_OF_WEEK | TIME | TIMER | 
          TODAYS_DATE MMDDYYYY? | TODAYS_NAME | YEAR | YYYYMMDD | YYYYDDD) ;

acceptFromEscapeKeyStatement : FROM ESCAPE KEY ;
acceptFromMnemonicStatement : FROM mnemonicName ;
acceptMessageCountStatement : MESSAGE? COUNT ;

displayStatement : 
    DISPLAY displayOperand+ displayAt? displayUpon? displayWith? 
    onExceptionClause? notOnExceptionClause? END_DISPLAY? ;

displayOperand : identifier | literal ;
displayAt : AT (identifier | literal) ;
displayUpon : UPON (mnemonicName | environmentName) ;
displayWith : WITH? NO ADVANCING ;

moveStatement : 
    MOVE ALL? (moveToStatement | moveCorrespondingToStatement) ;

moveToStatement : moveToSendingArea TO identifier+ ;
moveToSendingArea : identifier | literal ;
moveCorrespondingToStatement : 
    (CORRESPONDING | CORR) moveCorrespondingToSendingArea TO identifier+ ;
moveCorrespondingToSendingArea : identifier ;

performStatement : 
    PERFORM (performInlineStatement | performProcedureStatement) ;

performInlineStatement : 
    performType? statement* END_PERFORM ;

performProcedureStatement : 
    procedureName ((THROUGH | THRU) procedureName)? performType? ;

performType : performTimes | performUntil | performVarying ;
performTimes : (identifier | integerLiteral) TIMES ;
performUntil : performTestClause? UNTIL condition ;
performVarying : 
    performTestClause performVaryingClause | 
    performVaryingClause performTestClause? ;
performVaryingClause : 
    VARYING performVaryingPhrase performAfter* ;
performVaryingPhrase : 
    (identifier | literal) performFrom performBy performUntil ;
performAfter : AFTER performVaryingPhrase ;
performFrom : FROM (identifier | literal | arithmeticExpression) ;
performBy : BY (identifier | literal | arithmeticExpression) ;
performTestClause : WITH? (BEFORE | AFTER) ;

stopStatement : 
    STOP (RUN | literal | stopStatementGiving) ;

stopStatementGiving : 
    RUN (GIVING | RETURNING) (identifier | integerLiteral) ;

addStatement : 
    ADD (addToStatement | addToGivingStatement | addCorrespondingStatement) 
    onSizeErrorPhrase? notOnSizeErrorPhrase? END_ADD? ;

addToStatement : addFrom+ TO addTo+ ;
addToGivingStatement : 
    addFrom+ (TO addToGiving+)? GIVING addGiving+ ;
addCorrespondingStatement : 
    (CORRESPONDING | CORR) identifier TO addTo ;
addFrom : identifier | literal ;
addTo : identifier ROUNDED? ;
addToGiving : identifier | literal ;
addGiving : identifier ROUNDED? ;

computeStatement : 
    COMPUTE computeStore+ EQUALS_SIGN arithmeticExpression 
    onSizeErrorPhrase? notOnSizeErrorPhrase? END_COMPUTE? ;

computeStore : identifier ROUNDED? ;

ifStatement : IF condition ifThen ifElse? END_IF? ;
ifThen : THEN? (NEXT SENTENCE | statement*) ;
ifElse : ELSE (NEXT SENTENCE | statement*) ;

// Simplified versions of other statements for space
alterStatement : ALTER alterProceedTo+ ;
alterProceedTo : procedureName TO (PROCEED TO)? procedureName ;

allocateStatement : 
    ALLOCATE (integerLiteral | identifier) (CHARACTERS | BYTES)? 
    RETURNING (identifier | ADDRESS OF identifier) 
    onExceptionClause? notOnExceptionClause? END_ALLOCATE? ;

callStatement : 
    CALL (identifier | literal) callUsingPhrase? callGivingPhrase? 
    onOverflowPhrase? onExceptionClause? notOnExceptionClause? END_CALL? ;

callUsingPhrase : USING callUsingParameter+ ;
callUsingParameter : 
    callByReferencePhrase | callByValuePhrase | callByContentPhrase ;
callByReferencePhrase : 
    (BY? REFERENCE)? callByReference+ ;
callByReference : 
    ((ADDRESS OF | INTEGER | STRING)? identifier | literal | fileName) | 
    OMITTED ;
callByValuePhrase : BY? VALUE callByValue+ ;
callByValue : (ADDRESS OF | LENGTH OF?)? (identifier | literal) ;
callByContentPhrase : BY? CONTENT callByContent+ ;
callByContent : 
    (ADDRESS OF | LENGTH OF?)? identifier | literal | OMITTED ;
callGivingPhrase : (GIVING | RETURNING) identifier ;

cancelStatement : CANCEL cancelCall+ ;
cancelCall : 
    libraryName (BYTITLE | BYFUNCTION) | identifier | literal ;

closeStatement : CLOSE closeFile+ ;
closeFile : 
    fileName (closeReelUnitStatement | closeRelativeStatement | 
              closePortFileIOStatement)? ;
closeReelUnitStatement : 
    (REEL | UNIT) (FOR? REMOVAL)? (WITH? (NO REWIND | LOCK))? ;
closeRelativeStatement : WITH? (NO REWIND | LOCK) ;
closePortFileIOStatement : 
    (WITH? NO WAIT | WITH WAIT) (USING closePortFileIOUsing+)? ;
closePortFileIOUsingCloseDisposition : 
    CLOSE_DISPOSITION OF? (ABORT | ORDERLY) ;
closePortFileIOUsingAssociatedData : 
    ASSOCIATED_DATA (identifier | integerLiteral) ;
closePortFileIOUsingAssociatedDataLength : 
    ASSOCIATED_DATA_LENGTH OF? (identifier | integerLiteral) ;
closePortFileIOUsing : 
    closePortFileIOUsingCloseDisposition | 
    closePortFileIOUsingAssociatedData | 
    closePortFileIOUsingAssociatedDataLength ;

continueStatement : CONTINUE ;

deleteStatement : 
    DELETE fileName RECORD? invalidKeyPhrase? notInvalidKeyPhrase? 
    END_DELETE? ;

disableStatement : 
    DISABLE (INPUT TERMINAL? | I_O TERMINAL | OUTPUT) cdName 
    WITH? KEY (identifier | literal) ;

divideStatement : 
    DIVIDE (identifier | literal) 
    (divideIntoStatement | divideIntoGivingStatement | divideByGivingStatement) 
    divideRemainder? onSizeErrorPhrase? notOnSizeErrorPhrase? END_DIVIDE? ;

divideIntoStatement : INTO divideInto+ ;
divideIntoGivingStatement : 
    INTO (identifier | literal) divideGivingPhrase? ;
divideByGivingStatement : 
    BY (identifier | literal) divideGivingPhrase? ;
divideGivingPhrase : GIVING divideGiving+ ;
divideInto : identifier ROUNDED? ;
divideGiving : identifier ROUNDED? ;
divideRemainder : REMAINDER identifier ;

enableStatement : 
    ENABLE (INPUT TERMINAL? | I_O TERMINAL | OUTPUT) cdName 
    WITH? KEY (literal | identifier) ;

entryStatement : ENTRY literal (USING identifier+)? ;

evaluateStatement : 
    EVALUATE evaluateSelect evaluateAlsoSelect* evaluateWhenPhrase* 
    evaluateWhenOther? END_EVALUATE? ;

evaluateSelect : identifier | literal | arithmeticExpression | condition ;
evaluateAlsoSelect : ALSO evaluateSelect ;
evaluateWhenPhrase : evaluateWhen+ statement* ;
evaluateWhen : WHEN evaluateCondition evaluateAlsoCondition* ;
evaluateCondition : 
    ANY | NOT? evaluateValue evaluateThrough? | condition | booleanLiteral ;
evaluateThrough : (THROUGH | THRU) evaluateValue ;
evaluateAlsoCondition : ALSO evaluateCondition ;
evaluateWhenOther : WHEN OTHER statement* ;
evaluateValue : identifier | literal | arithmeticExpression ;

execCicsStatement : EXEC CICS execCicsLine+ END_EXEC ;
execCicsLine : 
    (IDENTIFIER | literal | operator | DOT | COMMA_CHAR | LPARENCHAR | 
     RPARENCHAR | EQUALS_SIGN | COLON)+ ;

execSqlImsStatement : EXEC SQL IMS execSqlImsLine+ END_EXEC ;
execSqlImsLine : 
    (IDENTIFIER | literal | operator | DOT | COMMA_CHAR | LPARENCHAR | 
     RPARENCHAR | EQUALS_SIGN | COLON)+ ;

exhibitStatement : EXHIBIT NAMED? CHANGED? exhibitOperand+ ;
exhibitOperand : identifier | literal ;

exitStatement : 
    EXIT (PROGRAM | METHOD | FUNCTION | PERFORM | PARAGRAPH | SECTION)? ;

freeStatement : 
    FREE (identifier | ADDRESS OF identifier) 
    onExceptionClause? notOnExceptionClause? END_FREE? ;

generateStatement : GENERATE reportName ;

gobackStatement : 
    GOBACK (GIVING | RAISING)? (identifier | literal)? ;

goToStatement : GO TO? (goToStatementSimple | goToDependingOnStatement) ;
goToStatementSimple : procedureName ;
goToDependingOnStatement : 
    procedureName+ (DEPENDING ON? identifier)? ;

initializeStatement : 
    INITIALIZE identifier+ initializeReplacingPhrase? ;

initializeReplacingPhrase : REPLACING initializeReplacingBy+ ;
initializeReplacingBy : 
    (ALPHABETIC | ALPHANUMERIC | ALPHANUMERIC_EDITED | NATIONAL | 
     NATIONAL_EDITED | NUMERIC | NUMERIC_EDITED | DBCS | EGCS) DATA? 
    BY (identifier | literal) ;

initiateStatement : INITIATE reportName+ ;

inspectStatement : 
    INSPECT identifier (inspectTallyingPhrase | inspectReplacingPhrase | 
                       inspectTallyingReplacingPhrase | inspectConvertingPhrase) ;

inspectTallyingPhrase : TALLYING inspectFor+ ;
inspectReplacingPhrase : 
    REPLACING (inspectReplacingCharacters | inspectReplacingAllLeadings)+ ;
inspectTallyingReplacingPhrase : 
    TALLYING inspectFor+ inspectReplacingPhrase+ ;
inspectConvertingPhrase : 
    CONVERTING (identifier | literal) inspectTo inspectBeforeAfter* ;
inspectFor : 
    identifier FOR (inspectCharacters | inspectAllLeadings)+ ;
inspectCharacters : 
    (CHARACTER | CHARACTERS) inspectBeforeAfter* ;
inspectReplacingCharacters : 
    (CHARACTER | CHARACTERS) inspectBy inspectBeforeAfter* ;
inspectAllLeadings : (ALL | LEADING) inspectAllLeading+ ;
inspectReplacingAllLeadings : 
    (ALL | LEADING | FIRST) inspectReplacingAllLeading+ ;
inspectAllLeading : (identifier | literal) inspectBeforeAfter* ;
inspectReplacingAllLeading : 
    (identifier | literal) inspectBy inspectBeforeAfter* ;
inspectBy : BY (identifier | literal) ;
inspectTo : TO (identifier | literal) ;
inspectBeforeAfter : 
    (BEFORE | AFTER) INITIAL? (identifier | literal) ;

invokeStatement : 
    INVOKE (identifier | SELF | SUPER) literal 
    (USING invokeUsingParameter*)? (RETURNING identifier)? 
    onExceptionClause? notOnExceptionClause? END_INVOKE? ;

invokeUsingParameter : 
    (BY REFERENCE | BY CONTENT | BY VALUE)? (identifier | literal) ;

jsonGenerateStatement : 
    JSON GENERATE identifier FROM identifier (NAME OF? identifier)? 
    (SUPPRESS identifier*)? onExceptionClause? notOnExceptionClause? 
    END_JSON ;

jsonParseStatement : 
    JSON PARSE identifier INTO identifier (NAME OF? identifier)? 
    onExceptionClause? notOnExceptionClause? END_JSON ;

mergeStatement : 
    MERGE fileName mergeOnKeyClause+ mergeCollatingSequencePhrase? 
    mergeUsing* mergeOutputProcedurePhrase? mergeGivingPhrase* ;

mergeOnKeyClause : 
    ON? (ASCENDING | DESCENDING) KEY? qualifiedDataName+ ;
mergeCollatingSequencePhrase : 
    COLLATING? SEQUENCE IS? alphabetName+ mergeCollatingAlphanumeric? 
    mergeCollatingNational? ;
mergeCollatingAlphanumeric : FOR? ALPHANUMERIC IS alphabetName ;
mergeCollatingNational : FOR? NATIONAL IS alphabetName ;
mergeUsing : USING fileName+ ;
mergeOutputProcedurePhrase : 
    OUTPUT PROCEDURE IS? procedureName mergeOutputThrough? ;
mergeOutputThrough : (THROUGH | THRU) procedureName ;
mergeGivingPhrase : GIVING mergeGiving+ ;
mergeGiving : 
    fileName (LOCK | SAVE | NO REWIND | CRUNCH | RELEASE | 
              WITH REMOVE CRUNCH)? ;

multiplyStatement : 
    MULTIPLY (identifier | literal) BY (multiplyRegular | multiplyGiving) 
    onSizeErrorPhrase? notOnSizeErrorPhrase? END_MULTIPLY? ;

multiplyRegular : multiplyRegularOperand+ ;
multiplyRegularOperand : identifier ROUNDED? ;
multiplyGiving : 
    multiplyGivingOperand GIVING multiplyGivingResult+ ;
multiplyGivingOperand : identifier | literal ;
multiplyGivingResult : identifier ROUNDED? ;

nextSentenceStatement : NEXT SENTENCE ;

openStatement : 
    OPEN (openInputStatement | openOutputStatement | openIOStatement | 
          openExtendStatement)+ ;

openInputStatement : INPUT openInput+ ;
openInput : fileName (REVERSED | WITH? NO REWIND)? ;
openOutputStatement : OUTPUT openOutput+ ;
openOutput : fileName (WITH? NO REWIND)? ;
openIOStatement : I_O fileName+ ;
openExtendStatement : EXTEND fileName+ ;

purgeStatement : PURGE cdName+ ;

raiseStatement : 
    RAISE (EXCEPTION | identifier) (WITH literal)? ;

readStatement : 
    READ fileName NEXT? RECORD? readInto? readWith? readKey? 
    invalidKeyPhrase? notInvalidKeyPhrase? atEndPhrase? notAtEndPhrase? 
    END_READ? ;

readInto : INTO identifier ;
readWith : WITH? ((KEPT | NO) LOCK | WAIT) ;
readKey : KEY IS? qualifiedDataName ;

receiveStatement : 
    RECEIVE (receiveFromStatement | receiveIntoStatement) 
    onExceptionClause? notOnExceptionClause? END_RECEIVE? ;

receiveFromStatement : 
    dataName FROM receiveFrom 
    (receiveBefore | receiveWith | receiveThread | receiveSize | 
     receiveStatus)* ;

receiveFrom : THREAD dataName | LAST THREAD | ANY THREAD ;
receiveIntoStatement : 
    cdName (MESSAGE | SEGMENT) INTO? identifier receiveNoData? 
    receiveWithData? ;
receiveNoData : NO DATA statement* ;
receiveWithData : WITH DATA statement* ;
receiveBefore : BEFORE TIME? (numericLiteral | identifier) ;
receiveWith : WITH? NO WAIT ;
receiveThread : THREAD IN? dataName ;
receiveSize : SIZE IN? (numericLiteral | identifier) ;
receiveStatus : STATUS IN? (identifier) ;

releaseStatement : RELEASE recordName (FROM qualifiedDataName)? ;

resumeStatement : RESUME (AT literal | NEXT STATEMENT) ;

returnStatement : 
    RETURN fileName RECORD? returnInto? atEndPhrase notAtEndPhrase? 
    END_RETURN? ;

returnInto : INTO qualifiedDataName ;

rewriteStatement : 
    REWRITE recordName rewriteFrom? invalidKeyPhrase? 
    notInvalidKeyPhrase? END_REWRITE? ;

rewriteFrom : FROM identifier ;

searchStatement : 
    SEARCH ALL? qualifiedDataName searchVarying? atEndPhrase? 
    searchWhen+ END_SEARCH? ;

searchVarying : VARYING qualifiedDataName ;
searchWhen : WHEN condition (NEXT SENTENCE | statement*) ;

sendStatement : 
    SEND (sendStatementSync | sendStatementAsync | sendStatementComm) 
    onExceptionClause? notOnExceptionClause? END_SEND? ;

sendStatementComm : 
    cdName sendFromPhrase? 
    (WITH (EGI | EMI | ESI | KEY (identifier | literal)))? ;
sendStatementSync : 
    SEND cdName (FROM identifier)? (WITH identifier)? END_SEND? ;
sendStatementAsync : TO (TOP | BOTTOM) identifier ;
sendFromPhrase : FROM identifier ;

setStatement : 
    SET (setToStatement+ | setUpDownByStatement | setConditionStatement) ;

setToStatement : setTo+ TO setToValue+ ;
setUpDownByStatement : setTo+ (UP BY | DOWN BY) setByValue ;
setConditionStatement : conditionName+ TO (TRUE | FALSE) ;
setTo : identifier ;
setToValue : 
    ON | OFF | ENTRY (identifier | literal) | identifier | literal ;
setByValue : identifier | literal ;

sortStatement : 
    SORT fileName sortOnKeyClause+ sortDuplicatesPhrase? 
    sortCollatingSequencePhrase? sortInputProcedurePhrase? sortUsing* 
    sortOutputProcedurePhrase? sortGivingPhrase* ;

sortOnKeyClause : 
    ON? (ASCENDING | DESCENDING) KEY? qualifiedDataName+ ;
sortDuplicatesPhrase : WITH? DUPLICATES IN? ORDER? ;
sortCollatingSequencePhrase : 
    COLLATING? SEQUENCE IS? alphabetName+ sortCollatingAlphanumeric? 
    sortCollatingNational? ;
sortCollatingAlphanumeric : FOR? ALPHANUMERIC IS alphabetName ;
sortCollatingNational : FOR? NATIONAL IS alphabetName ;
sortInputProcedurePhrase : 
    INPUT PROCEDURE IS? procedureName sortInputThrough? ;
sortInputThrough : (THROUGH | THRU) procedureName ;
sortUsing : USING fileName+ ;
sortOutputProcedurePhrase : 
    OUTPUT PROCEDURE IS? procedureName sortOutputThrough? ;
sortOutputThrough : (THROUGH | THRU) procedureName ;
sortGivingPhrase : GIVING sortGiving+ ;
sortGiving : 
    fileName (LOCK | SAVE | NO REWIND | CRUNCH | RELEASE | 
              WITH REMOVE CRUNCH)? ;

startStatement : 
    START fileName startKey? invalidKeyPhrase? notInvalidKeyPhrase? 
    END_START? ;

startKey : 
    KEY IS? (EQUAL TO? | EQUALS | GREATER THAN? | MORETHANCHAR | 
             NOT LESS THAN? | NOT LESSTHANCHAR | GREATER THAN? OR EQUAL TO? | 
             GREATER_THAN_OR_EQUAL) qualifiedDataName ;

stringStatement : 
    STRING stringSendingPhrase+ stringIntoPhrase stringWithPointerPhrase? 
    onOverflowPhrase? notOnOverflowPhrase? END_STRING? ;

stringSendingPhrase : 
    stringSending (COMMA_CHAR? stringSending)* 
    (stringDelimitedByPhrase | stringForPhrase) ;
stringSending : identifier | literal ;
stringDelimitedByPhrase : DELIMITED BY? (SIZE | identifier | literal) ;
stringForPhrase : FOR (identifier | literal) ;
stringIntoPhrase : INTO identifier ;
stringWithPointerPhrase : WITH? POINTER qualifiedDataName ;

subtractStatement : 
    SUBTRACT (subtractFromStatement | subtractFromGivingStatement | 
              subtractCorrespondingStatement) 
    onSizeErrorPhrase? notOnSizeErrorPhrase? END_SUBTRACT? ;

subtractFromStatement : subtractSubtrahend+ FROM subtractMinuend+ ;
subtractFromGivingStatement : 
    subtractSubtrahend+ FROM subtractMinuendGiving GIVING subtractGiving+ ;
subtractCorrespondingStatement : 
    (CORRESPONDING | CORR) qualifiedDataName FROM 
    subtractMinuendCorresponding ;
subtractSubtrahend : identifier | literal ;
subtractMinuend : identifier ROUNDED? ;
subtractMinuendGiving : identifier | literal ;
subtractGiving : identifier ROUNDED? ;
subtractMinuendCorresponding : qualifiedDataName ROUNDED? ;

terminateStatement : TERMINATE reportName ;

unstringStatement : 
    UNSTRING unstringSendingPhrase unstringIntoPhrase 
    unstringWithPointerPhrase? unstringTallyingPhrase? onOverflowPhrase? 
    notOnOverflowPhrase? END_UNSTRING? ;

unstringSendingPhrase : 
    identifier (unstringDelimitedByPhrase unstringOrAllPhrase*)? ;
unstringDelimitedByPhrase : 
    DELIMITED BY? ALL? (identifier | literal) ;
unstringOrAllPhrase : OR ALL? (identifier | literal) ;
unstringIntoPhrase : INTO unstringInto+ ;
unstringInto : 
    identifier unstringDelimiterIn? unstringCountIn? ;
unstringDelimiterIn : DELIMITER IN? identifier ;
unstringCountIn : COUNT IN? identifier ;
unstringWithPointerPhrase : WITH? POINTER qualifiedDataName ;
unstringTallyingPhrase : TALLYING IN? qualifiedDataName ;

useStatement : 
    USE (useAfterClause | useDebugClause | useBeforeReportingClause | 
         useExceptionClause | useGlobalClause) ;

useAfterClause : 
    AFTER STANDARD? (ERROR | EXCEPTION) PROCEDURE? ON 
    (fileName+ | INPUT | OUTPUT | I_O | EXTEND) ;
useDebugClause : 
    FOR? DEBUGGING ON (procedureName | ALL PROCEDURES | fileName | 
                      mnemonicName) ;
useBeforeReportingClause : BEFORE REPORTING reportName ;
useExceptionClause : AFTER EXCEPTION CONDITION ;
useGlobalClause : GLOBAL ;

writeStatement : 
    WRITE recordName writeFromPhrase? writeAdvancingPhrase? 
    writeAtEndOfPagePhrase? writeNotAtEndOfPagePhrase? invalidKeyPhrase? 
    notInvalidKeyPhrase? END_WRITE? ;

writeFromPhrase : FROM (identifier | literal) ;
writeAdvancingPhrase : 
    (BEFORE | AFTER) ADVANCING? 
    (writeAdvancingPage | writeAdvancingLines | writeAdvancingMnemonic) ;
writeAdvancingPage : PAGE ;
writeAdvancingLines : (identifier | literal) (LINE | LINES)? ;
writeAdvancingMnemonic : mnemonicName ;
writeAtEndOfPagePhrase : AT? (END_OF_PAGE | EOP) statement* ;
writeNotAtEndOfPagePhrase : NOT AT? (END_OF_PAGE | EOP) statement* ;

xmlGenerateStatement : 
    XML GENERATE identifier FROM identifier (COUNT IN? identifier)? 
    (NAMESPACE identifier)? (NAMESPACE_PREFIX identifier)? 
    onExceptionClause? notOnExceptionClause? END_XML ;

xmlParseStatement : 
    XML PARSE identifier PROCESSING PROCEDURE IS? procedureName 
    xmlParseOptions* onExceptionClause? notOnExceptionClause? END_XML ;

xmlParseOptions : 
    VALIDATING WITH? (xmlSchemaName | FILE literal) | 
    RETURNING NATIONAL | ENCODING literal ;
xmlSchemaName : identifier ;

/*
================================================================================
EXCEPTION HANDLING PHRASES
================================================================================
*/

atEndPhrase : AT? END statement* ;
notAtEndPhrase : NOT AT? END statement* ;
invalidKeyPhrase : INVALID KEY? statement* ;
notInvalidKeyPhrase : NOT INVALID KEY? statement* ;
onOverflowPhrase : ON? OVERFLOW statement* ;
notOnOverflowPhrase : NOT ON? OVERFLOW statement* ;
onSizeErrorPhrase : ON? SIZE ERROR statement* ;
notOnSizeErrorPhrase : NOT ON? SIZE ERROR statement* ;
onExceptionClause : ON? EXCEPTION statement* ;
notOnExceptionClause : NOT ON? EXCEPTION statement* ;

/*
================================================================================
ARITHMETIC EXPRESSIONS
================================================================================
*/

arithmeticExpression : multDivs plusMinus* ;
plusMinus : (PLUSCHAR | MINUSCHAR) multDivs ;
multDivs : powers multDiv* ;
multDiv : (ASTERISK | SLASH) powers ;
powers : (PLUSCHAR | MINUSCHAR)? basis power* ;
power : DOUBLEASTERISK basis ;
basis : 
    LPARENCHAR arithmeticExpression RPARENCHAR | identifier | literal ;

/*
================================================================================
CONDITIONS
================================================================================
*/

condition : combinableCondition andOrCondition* ;
andOrCondition : (AND | OR) (combinableCondition | abbreviation+) ;
combinableCondition : NOT? simpleCondition ;
simpleCondition : 
    LPARENCHAR condition RPARENCHAR | relationCondition | 
    classCondition | conditionNameReference ;

classCondition : 
    identifier IS? NOT? 
    (NUMERIC | ALPHABETIC | ALPHABETIC_LOWER | ALPHABETIC_UPPER | 
     DBCS | KANJI | className) ;

conditionNameReference : 
    conditionName (inData* inFile? conditionNameSubscriptReference* | 
                  inMnemonic*) ;

conditionNameSubscriptReference : 
    LPARENCHAR subscript (COMMA_CHAR? subscript)* RPARENCHAR ;

relationCondition : 
    relationSignCondition | relationArithmeticComparison | 
    relationCombinedComparison ;

relationSignCondition : 
    arithmeticExpression IS? NOT? (POSITIVE | NEGATIVE | ZERO) ;

relationArithmeticComparison : 
    arithmeticExpression relationalOperator arithmeticExpression ;

relationCombinedComparison : 
    arithmeticExpression relationalOperator LPARENCHAR 
    relationCombinedCondition RPARENCHAR ;

relationCombinedCondition : 
    arithmeticExpression ((AND | OR) arithmeticExpression)+ ;

relationalOperator : 
    (IS | ARE)? (NOT? (GREATER THAN? | MORETHANCHAR | LESS THAN? | 
                      LESSTHANCHAR | EQUAL TO? | EQUALS) | 
                NOT_EQUAL | GREATER_THAN_OR_EQUAL | LESS_THAN_OR_EQUAL) ;

abbreviation : 
    NOT? relationalOperator? 
    (arithmeticExpression | LPARENCHAR arithmeticExpression abbreviation 
                           RPARENCHAR) ;

/*
================================================================================
IDENTIFIERS AND REFERENCES
================================================================================
*/

identifier : 
    qualifiedDataName | tableCall | functionCall | specialRegister | 
    objectReference | methodReference ;

tableCall : 
    qualifiedDataName (LPARENCHAR subscript (COMMA_CHAR? subscript)* 
                      RPARENCHAR)* referenceModifier? ;

functionCall : 
    FUNCTION functionName (LPARENCHAR argument (COMMA_CHAR? argument)* 
                          RPARENCHAR)* referenceModifier? ;

objectReference : 
    qualifiedDataName OBJECT_REFERENCE_OP qualifiedDataName ;

methodReference : 
    qualifiedDataName METHOD_REFERENCE_OP methodName ;

referenceModifier : 
    LPARENCHAR characterPosition COLON length? RPARENCHAR ;

characterPosition : arithmeticExpression ;
length : arithmeticExpression ;

subscript : 
    ALL | integerLiteral | qualifiedDataName integerLiteral? | 
    indexName integerLiteral? | arithmeticExpression ;

argument : 
    literal | identifier | qualifiedDataName integerLiteral? | 
    indexName integerLiteral? | arithmeticExpression ;

qualifiedDataName : 
    qualifiedDataNameFormat1 | qualifiedDataNameFormat2 | 
    qualifiedDataNameFormat3 | qualifiedDataNameFormat4 ;

qualifiedDataNameFormat1 : 
    (dataName | conditionName) (qualifiedInData+ inFile? | inFile)? ;

qualifiedDataNameFormat2 : paragraphName inSection ;

qualifiedDataNameFormat3 : textName inLibrary ;

qualifiedDataNameFormat4 : LINAGE_COUNTER inFile ;

qualifiedInData : inData | inTable ;

inData : (IN | OF) dataName ;
inFile : (IN | OF) fileName ;
inMnemonic : (IN | OF) mnemonicName ;
inSection : (IN | OF) sectionName ;
inLibrary : (IN | OF) libraryName ;
inTable : (IN | OF) tableCall ;

/*
================================================================================
NAME DEFINITIONS
================================================================================
*/

alphabetName : cobolWord ;
assignmentName : systemName ;
basisName : programName ;
cdName : cobolWord ;
className : cobolWord ;
computerName : systemName ;
conditionName : cobolWord ;
dataName : cobolWord ;
dataDescName : FILLER | CURSOR | dataName ;
environmentName : systemName ;
fileName : cobolWord ;
functionName : 
    INTEGER | LENGTH | RANDOM | SUM | WHEN_COMPILED | cobolWord ;
indexName : cobolWord ;
interfaceName : cobolWord ;
languageName : systemName ;
libraryName : cobolWord ;
localName : cobolWord ;
methodName : cobolWord ;
mnemonicName : cobolWord ;
paragraphName : cobolWord | integerLiteral ;
procedureName : paragraphName inSection? | sectionName ;
programName : NONNUMERICLITERAL | cobolWord | literal ;
recordName : qualifiedDataName ;
reportName : qualifiedDataName ;
routineName : cobolWord ;
screenName : cobolWord ;
sectionName : cobolWord | integerLiteral ;
systemName : cobolWord ;
symbolicCharacter : cobolWord ;
textName : cobolWord ;
cobolWord : IDENTIFIER ;

/*
================================================================================
LITERALS AND CONSTANTS
================================================================================
*/

literal : 
    NONNUMERICLITERAL | figurativeConstant | numericLiteral | 
    booleanLiteral | cicsDfhRespLiteral | cicsDfhValueLiteral ;

booleanLiteral : TRUE | FALSE ;

numericLiteral : NUMERICLITERAL | ZERO | integerLiteral ;

integerLiteral : 
    NUMERICLITERAL | INTEGERLITERAL | LEVEL_NUMBER_01 | LEVEL_NUMBER_02_49 
    | LEVEL_NUMBER_66 | LEVEL_NUMBER_77 | LEVEL_NUMBER_88 ;

// FIXED: Enhanced level number support - these tokens must come BEFORE levelNumber rule
LEVEL_NUMBER_01 : '01' | '1' ;
LEVEL_NUMBER_02_49 : 
    '02' | '03' | '04' | '05' | '06' | '07' | '08' | '09' | '10' |
    '11' | '12' | '13' | '14' | '15' | '16' | '17' | '18' | '19' |
    [2-4][0-9] ;
LEVEL_NUMBER_66 : '66' ;
LEVEL_NUMBER_77 : '77' ;
LEVEL_NUMBER_88 : '88' ;

// FIXED: Enhanced level number support for all valid COBOL levels
levelNumber
    : LEVEL_NUMBER_01
    | LEVEL_NUMBER_02_49  
    | LEVEL_NUMBER_66
    | LEVEL_NUMBER_77
    | LEVEL_NUMBER_88
    ;

levelNumberLiteral : NUMERICLITERAL ;

cicsDfhRespLiteral : 
    DFHRESP LPARENCHAR (cobolWord | literal) RPARENCHAR ;

cicsDfhValueLiteral : 
    DFHVALUE LPARENCHAR (cobolWord | literal) RPARENCHAR ;

figurativeConstant : 
    ALL literal | HIGH_VALUE | HIGH_VALUES | LOW_VALUE | LOW_VALUES | 
    NULL | NULLS | QUOTE | QUOTES | SPACE | SPACES | ZERO | ZEROS | ZEROES ;

specialRegister : 
    ADDRESS OF identifier | DATE | DAY | DAY_OF_WEEK | DEBUG_CONTENTS | 
    DEBUG_ITEM | DEBUG_LINE | DEBUG_NAME | DEBUG_SUB_1 | DEBUG_SUB_2 | 
    DEBUG_SUB_3 | LENGTH OF? identifier | LINAGE_COUNTER | LINE_COUNTER | 
    PAGE_COUNTER | RETURN_CODE | SHIFT_IN | SHIFT_OUT | SORT_CONTROL | 
    SORT_CORE_SIZE | SORT_FILE_SIZE | SORT_MESSAGE | SORT_MODE_SIZE | 
    SORT_RETURN | TALLY | TIME | WHEN_COMPILED ;

operator : 
    PLUSCHAR | MINUSCHAR | ASTERISK | SLASH | DOUBLEASTERISK | EQUALS_SIGN | 
    NOT_EQUAL | LESSTHANCHAR | MORETHANCHAR | LESS_THAN_OR_EQUAL | 
    GREATER_THAN_OR_EQUAL | AMPERSAND | DOLLAR ;

/*
================================================================================
LEXER RULES - ENHANCED FOR BETTER PARSING
================================================================================
*/

// Dot should come before comment entry
DOT : '.' ;

// Whitespace handling
NEWLINE : '\r'? '\n' -> skip ;
WS : [ \t]+ -> skip ;

// Enhanced comment handling for COBOL format
COMMENTENTRYLINE : 
    ('*' | '/') ~[\r\n]* -> channel(HIDDEN) ;

// Line continuation handling
CONTINUATION_LINE : 
    [0-9] [0-9] [0-9] [0-9] [0-9] [0-9] '-' ~[\r\n]* -> channel(HIDDEN) ;

// Punctuation and operators
COMMA_CHAR : ',' ;
SEMICOLON : ';' ;
COLON : ':' ;
LPARENCHAR : '(' ;
RPARENCHAR : ')' ;
LBRACKET : '[' ;
RBRACKET : ']' ;
PLUSCHAR : '+' ;
MINUSCHAR : '-' ;
ASTERISK : '*' ;
DOUBLEASTERISK : '**' ;
SLASH : '/' ;
EQUALS_SIGN : '=' ;
NOT_EQUAL : '<>' | '!=' | '≠' ;
LESSTHANCHAR : '<' ;
MORETHANCHAR : '>' ;
LESS_THAN_OR_EQUAL : '<=' | '≤' ;
GREATER_THAN_OR_EQUAL : '>=' | '≥' ;
AMPERSAND : '&' ;
DOLLAR : '$' ;

// Object-oriented operators
OBJECT_REFERENCE_OP : '::' ;
METHOD_REFERENCE_OP : '->' ;

// Literals with enhanced support
NONNUMERICLITERAL : 
    ('"' (~["\r\n] | '""')* '"' | 
     '\'' (~['\r\n] | '\'\'')* '\'' | 
     'X"' [0-9A-Fa-f]* '"' | 
     'H"' [0-9A-Fa-f]* '"' |
     'Z"' (~["\r\n])* '"') ;

NUMERICLITERAL : 
    [0-9]+ ('.' [0-9]+)? ([eE] [+-]? [0-9]+)? ;

INTEGERLITERAL : [0-9]+ ;

// FIXED: Picture string token - handles COBOL picture clauses better
PICTURE_STRING : [XANSVPZBEGUxansvpzbegu9$*+.,/<>=-]+ ;

// Pseudo text delimiter
PSEUDO_TEXT_DELIMITER : '==' ;

// Sequence area handling (for fixed format COBOL)
SEQUENCE_AREA : 
    {getCharPositionInLine() > 50}? [A-Za-z0-9.-]+ -> channel(HIDDEN) ;

/*
================================================================================
COBOL KEYWORDS (Case-insensitive) - ENHANCED
================================================================================
*/

// Division keywords
IDENTIFICATION : I D E N T I F I C A T I O N ;
ENVIRONMENT : E N V I R O N M E N T ;
DATA : D A T A ;
PROCEDURE : P R O C E D U R E ;
DIVISION : D I V I S I O N ;

// Section keywords
CONFIGURATION : C O N F I G U R A T I O N ;
INPUT_OUTPUT : I N P U T '-' O U T P U T ;
FILE_CONTROL : F I L E '-' C O N T R O L ;
I_O_CONTROL : I '-' O '-' C O N T R O L ;
FILE : F I L E ;
WORKING_STORAGE : W O R K I N G '-' S T O R A G E ;
LINKAGE : L I N K A G E ;
COMMUNICATION : C O M M U N I C A T I O N ;
LOCAL_STORAGE : L O C A L '-' S T O R A G E ;
SCREEN : S C R E E N ;
REPORT : R E P O R T ;
PROGRAM_LIBRARY : P R O G R A M '-' L I B R A R Y ;
DATA_BASE : D A T A '-' B A S E ;
SECTION : S E C T I O N ;

PROGRAM_ID : P R O G R A M '-' I D ;
ID : I D ;

// Basic keywords
ABORT : A B O R T ;
ACCEPT : A C C E P T ;
ACCESS : A C C E S S ;
ADD : A D D ;
ADDRESS : A D D R E S S ;
ADVANCING : A D V A N C I N G ;
AFTER : A F T E R ;
ALIGNED : A L I G N E D ;
ALL : A L L ;
ALLOCATE : A L L O C A T E ;
ALPHABET : A L P H A B E T ;
ALPHABETIC : A L P H A B E T I C ;
ALPHABETIC_LOWER : A L P H A B E T I C '-' L O W E R ;
ALPHABETIC_UPPER : A L P H A B E T I C '-' U P P E R ;
ALPHANUMERIC : A L P H A N U M E R I C ;
ALPHANUMERIC_EDITED : A L P H A N U M E R I C '-' E D I T E D ;
ALSO : A L S O ;
ALTER : A L T E R ;
ALTERNATE : A L T E R N A T E ;
AND : A N D ;
ANY : A N Y ;
ARE : A R E ;
AREA : A R E A ;
AREAS : A R E A S ;
AS : A S ;
ASCENDING : A S C E N D I N G ;
ASCII : A S C I I ;
ASSIGN : A S S I G N ;
ASSOCIATED_DATA : A S S O C I A T E D '-' D A T A ;
ASSOCIATED_DATA_LENGTH : A S S O C I A T E D '-' D A T A '-' L E N G T H ;
AT : A T ;
ATTRIBUTE : A T T R I B U T E ;
AUTHOR : A U T H O R ;
AUTO : A U T O ;
AUTO_SKIP : A U T O '-' S K I P ;
AUTOMATIC : A U T O M A T I C ;

// B keywords
BACKGROUND_COLOR : B A C K G R O U N D '-' C O L O R ;
BACKGROUND_COLOUR : B A C K G R O U N D '-' C O L O U R ;
BASED : B A S E D ;
BEEP : B E E P ;
BEFORE : B E F O R E ;
BELL : B E L L ;
BINARY : B I N A R Y ;
BIT : B I T ;
BLANK : B L A N K ;
BLINK : B L I N K ;
BLOB : B L O B ;
BLOCK : B L O C K ;
BOTTOM : B O T T O M ;
BOUNDS : B O U N D S ;
BY : B Y ;
BYFUNCTION : B Y F U N C T I O N ;
BYTES : B Y T E S ;
BYTITLE : B Y T I T L E ;

// C keywords
CALL : C A L L ;
CANCEL : C A N C E L ;
CAPABLE : C A P A B L E ;
CCSVERSION : C C S V E R S I O N ;
CD : C D ;
CF : C F ;
CH : C H ;
CHAINING : C H A I N I N G ;
CHANGED : C H A N G E D ;
CHANNEL : C H A N N E L ;
CHARACTER : C H A R A C T E R ;
CHARACTERS : C H A R A C T E R S ;
CICS : C I C S ;
CLASS : C L A S S ;
CLASS_ID : C L A S S '-' I D ;
CLOB : C L O B ;
CLOCK_UNITS : C L O C K '-' U N I T S ;
CLOSE : C L O S E ;
CLOSE_DISPOSITION : C L O S E '-' D I S P O S I T I O N ;
COBOL : C O B O L ;
CODE_SET : C O D E '-' S E T ;
COL : C O L ;
COLLATING : C O L L A T I N G ;
COLUMN : C O L U M N ;
COMMA : C O M M A ;
COMMITMENT : C O M M I T M E N T ;
COMMON : C O M M O N ;
COMP : C O M P ;
COMP_1 : C O M P '-' '1' ;
COMP_2 : C O M P '-' '2' ;
COMP_3 : C O M P '-' '3' ;
COMP_4 : C O M P '-' '4' ;
COMP_5 : C O M P '-' '5' ;
COMP_6 : C O M P '-' '6' ;
COMPUTATIONAL : C O M P U T A T I O N A L ;
COMPUTATIONAL_1 : C O M P U T A T I O N A L '-' '1' ;
COMPUTATIONAL_2 : C O M P U T A T I O N A L '-' '2' ;
COMPUTATIONAL_3 : C O M P U T A T I O N A L '-' '3' ;
COMPUTATIONAL_4 : C O M P U T A T I O N A L '-' '4' ;
COMPUTATIONAL_5 : C O M P U T A T I O N A L '-' '5' ;
COMPUTATIONAL_6 : C O M P U T A T I O N A L '-' '6' ;
COMPUTE : C O M P U T E ;
CONTAINS : C O N T A I N S ;
CONTENT : C O N T E N T ;
CONTINUE : C O N T I N U E ;
CONTROL : C O N T R O L ;
CONTROL_POINT : C O N T R O L '-' P O I N T ;
CONVENTION : C O N V E N T I O N ;
CONVERTING : C O N V E R T I N G ;
COPY : C O P Y ;
CORR : C O R R ;
CORRESPONDING : C O R R E S P O N D I N G ;
COUNT : C O U N T ;
CRUNCH : C R U N C H ;
CURRENCY : C U R R E N C Y ;
CURSOR : C U R S O R ;

// D keywords  
DATE : D A T E ;
DATE_COMPILED : D A T E '-' C O M P I L E D ;
DATE_WRITTEN : D A T E '-' W R I T T E N ;
DAY : D A Y ;
DAY_OF_WEEK : D A Y '-' O F '-' W E E K ;
DBCS : D B C S ;
DBCLOB : D B C L O B ;
DE : D E ;
DEBUG_CONTENTS : D E B U G '-' C O N T E N T S ;
DEBUG_ITEM : D E B U G '-' I T E M ;
DEBUG_LINE : D E B U G '-' L I N E ;
DEBUG_NAME : D E B U G '-' N A M E ;
DEBUG_SUB_1 : D E B U G '-' S U B '-' '1' ;
DEBUG_SUB_2 : D E B U G '-' S U B '-' '2' ;
DEBUG_SUB_3 : D E B U G '-' S U B '-' '3' ;
DEBUGGING : D E B U G G I N G ;
DECIMAL_POINT : D E C I M A L '-' P O I N T ;
DECLARATIVES : D E C L A R A T I V E S ;
DEFAULT : D E F A U L T ;
DEFAULT_DISPLAY : D E F A U L T '-' D I S P L A Y ;
DEFINITION : D E F I N I T I O N ;
DELETE : D E L E T E ;
DELIMITED : D E L I M I T E D ;
DELIMITER : D E L I M I T E R ;
DEPENDING : D E P E N D I N G ;
DESCENDING : D E S C E N D I N G ;
DESTINATION : D E S T I N A T I O N ;
DETAIL : D E T A I L ;
DFHRESP : D F H R E S P ;
DFHVALUE : D F H V A L U E ;
DISABLE : D I S A B L E ;
DISK : D I S K ;
DISPLAY : D I S P L A Y ;
DISPLAY_1 : D I S P L A Y '-' '1' ;
DIVIDE : D I V I D E ;
DONTCARE : D O N T C A R E ;
DOUBLE : D O U B L E ;
DOWN : D O W N ;
DUPLICATES : D U P L I C A T E S ;
DYNAMIC : D Y N A M I C ;

// E keywords
EBCDIC : E B C D I C ;
EGCS : E G C S ;
EGI : E G I ;
ELSE : E L S E ;
EMI : E M I ;
EMPTY_CHECK : E M P T Y '-' C H E C K ;
ENABLE : E N A B L E ;
ENCODING : E N C O D I N G ;
END : E N D ;
END_ACCEPT : E N D '-' A C C E P T ;
END_ADD : E N D '-' A D D ;
END_ALLOCATE : E N D '-' A L L O C A T E ;
END_CALL : E N D '-' C A L L ;
END_COMPUTE : E N D '-' C O M P U T E ;
END_DELETE : E N D '-' D E L E T E ;
END_DISPLAY : E N D '-' D I S P L A Y ;
END_DIVIDE : E N D '-' D I V I D E ;
END_EVALUATE : E N D '-' E V A L U A T E ;
END_EXEC : E N D '-' E X E C ;
END_FREE : E N D '-' F R E E ;
END_IF : E N D '-' I F ;
END_INVOKE : E N D '-' I N V O K E ;
END_JSON : E N D '-' J S O N ;
END_MULTIPLY : E N D '-' M U L T I P L Y ;
END_OF_PAGE : E N D '-' O F '-' P A G E ;
END_PERFORM : E N D '-' P E R F O R M ;
END_PROGRAM : E N D ' ' P R O G R A M | E N D '-' P R O G R A M ;
END_READ : E N D '-' R E A D ;
END_RECEIVE : E N D '-' R E C E I V E ;
END_RETURN : E N D '-' R E T U R N ;
END_REWRITE : E N D '-' R E W R I T E ;
END_SEARCH : E N D '-' S E A R C H ;
END_SEND : E N D '-' S E N D | E N D ' ' S E N D ;
END_START : E N D '-' S T A R T ;
END_STRING : E N D '-' S T R I N G ;
END_SUBTRACT : E N D '-' S U B T R A C T ;
END_UNSTRING : E N D '-' U N S T R I N G ;
END_WRITE : E N D '-' W R I T E ;
END_XML : E N D '-' X M L ;
ENTER : E N T E R ;
ENTRY : E N T R Y ;
ENTRY_PROCEDURE : E N T R Y '-' P R O C E D U R E ;
EOL : E O L ;
EOP : E O P ;
EOS : E O S ;
EQUAL : E Q U A L ;
EQUALS : E Q U A L S ;
ERROR : E R R O R ;
ESCAPE : E S C A P E ;
ESI : E S I ;
EVALUATE : E V A L U A T E ;
EVENT : E V E N T ;
EVERY : E V E R Y ;
EXCEPTION : E X C E P T I O N ;
EXCLUSIVE : E X C L U S I V E ;
EXEC : E X E C ;
EXHIBIT : E X H I B I T ;
EXIT : E X I T ;
EXPORT : E X P O R T ;
EXTEND : E X T E N D ;
EXTENDED : E X T E N D E D ;
EXTERNAL : E X T E R N A L ;

// F keywords
FACTORY : F A C T O R Y ;
FALSE : F A L S E ;
FD : F D ;
FILLER : F I L L E R ;
FINAL : F I N A L ;
FIRST : F I R S T ;
FLOAT_BINARY_32 : F L O A T '-' B I N A R Y '-' '3' '2' ;
FLOAT_BINARY_64 : F L O A T '-' B I N A R Y '-' '6' '4' ;
FLOAT_DECIMAL_16 : F L O A T '-' D E C I M A L '-' '1' '6' ;
FLOAT_DECIMAL_34 : F L O A T '-' D E C I M A L '-' '3' '4' ;
FLOAT_EXTENDED : F L O A T '-' E X T E N D E D ;
FOOTING : F O O T I N G ;
FOR : F O R ;
FOREGROUND_COLOR : F O R E G R O U N D '-' C O L O R ;
FOREGROUND_COLOUR : F O R E G R O U N D '-' C O L O U R ;
FREE : F R E E ;
FROM : F R O M ;
FULL : F U L L ;
FUNCTION : F U N C T I O N ;
FUNCTION_ID : F U N C T I O N '-' I D ;
FUNCTIONNAME : F U N C T I O N N A M E ;
FUNCTION_POINTER : F U N C T I O N '-' P O I N T E R ;

// Continue with remaining keywords...
GENERATE : G E N E R A T E ;
GIVING : G I V I N G ;
GLOBAL : G L O B A L ;
GO : G O ;
GOBACK : G O B A C K ;
GREATER : G R E A T E R ;
GRID : G R I D ;
GROUP : G R O U P ;

HEADING : H E A D I N G ;
HIGH_VALUE : H I G H '-' V A L U E ;
HIGH_VALUES : H I G H '-' V A L U E S ;
HIGHLIGHT : H I G H L I G H T ;

I_O : I '-' O ;
IF : I F ;
IMS : I M S ;
IMPLICIT : I M P L I C I T ;
IMPORT : I M P O R T ;
IN : I N ;
INCLUDE : I N C L U D E ;
INDEX : I N D E X ;
INDEXED : I N D E X E D ;
INDICATE : I N D I C A T E ;
INHERITS : I N H E R I T S ;
INITIAL : I N I T I A L ;
INITIALIZE : I N I T I A L I Z E ;
INITIATE : I N I T I A T E ;
INPUT : I N P U T ;
INSPECT : I N S P E C T ;
INSTALLATION : I N S T A L L A T I O N ;
INTEGER : I N T E G E R ;
INTERFACE : I N T E R F A C E ;
INTERFACE_ID : I N T E R F A C E '-' I D ;
INT : I N T ;
INTO : I N T O ;
INTRINSIC : I N T R I N S I C ;
INVALID : I N V A L I D ;
INVOKE : I N V O K E ;
IS : I S ;

JSON : J S O N ;
JUST : J U S T ;
JUSTIFIED : J U S T I F I E D ;

KANJI : K A N J I ;
KEPT : K E P T ;
KEY : K E Y ;
KEYBOARD : K E Y B O A R D ;

LABEL : L A B E L ;
LANGUAGE : L A N G U A G E ;
LAST : L A S T ;
LB : L B ;
LD : L D ;
LEADING : L E A D I N G ;
LEFT : L E F T ;
LEFTLINE : L E F T L I N E ;
LENGTH : L E N G T H ;
LENGTH_CHECK : L E N G T H '-' C H E C K ;
LESS : L E S S ;
LIBACCESS : L I B A C C E S S ;
LIBPARAMETER : L I B P A R A M E T E R ;
LIBRARY : L I B R A R Y ;
LIMIT : L I M I T ;
LIMITS : L I M I T S ;
LINAGE : L I N A G E ;
LINAGE_COUNTER : L I N A G E '-' C O U N T E R ;
LINE : L I N E ;
LINE_COUNTER : L I N E '-' C O U N T E R ;
LINES : L I N E S ;
LIST : L I S T ;
LOCAL : L O C A L ;
LOCK : L O C K ;
LONG_DATE : L O N G '-' D A T E ;
LONG_TIME : L O N G '-' T I M E ;
LOW_VALUE : L O W '-' V A L U E ;
LOW_VALUES : L O W '-' V A L U E S ;
LOWER : L O W E R ;
LOWLIGHT : L O W L I G H T ;

MANUAL : M A N U A L ;
MEMORY : M E M O R Y ;
MERGE : M E R G E ;
MESSAGE : M E S S A G E ;
METHOD : M E T H O D ;
METHOD_ID : M E T H O D '-' I D ;
MMDDYYYY : M M D D Y Y Y Y ;
MODE : M O D E ;
MODULES : M O D U L E S ;
MOVE : M O V E ;
MULTIPLE : M U L T I P L E ;
MULTIPLY : M U L T I P L Y ;

NAME : N A M E ;
NAMED : N A M E D ;
NAMESPACE : N A M E S P A C E ;
NAMESPACE_PREFIX : N A M E S P A C E '-' P R E F I X ;
NATIONAL : N A T I O N A L ;
NATIONAL_EDITED : N A T I O N A L '-' E D I T E D ;
NATIVE : N A T I V E ;
NEGATIVE : N E G A T I V E ;
NETWORK : N E T W O R K ;
NEXT : N E X T ;
NO : N O ;
NO_ECHO : N O '-' E C H O ;
NOT : N O T ;
NULL : N U L L ;
NULLS : N U L L S ;
NUMBER : N U M B E R ;
NUMERIC : N U M E R I C ;
NUMERIC_DATE : N U M E R I C '-' D A T E ;
NUMERIC_EDITED : N U M E R I C '-' E D I T E D ;
NUMERIC_TIME : N U M E R I C '-' T I M E ;

OBJECT : O B J E C T ;
OBJECT_COMPUTER : O B J E C T '-' C O M P U T E R ;
OBJECT_REFERENCE : O B J E C T '-' R E F E R E N C E ;
OCCURS : O C C U R S ;
ODT : O D T ;
OF : O F ;
OFF : O F F ;
OMITTED : O M I T T E D ;
ON : O N ;
ONLY : O N L Y ;
OPEN : O P E N ;
OPTIONAL : O P T I O N A L ;
OR : O R ;
ORDER : O R D E R ;
ORDERLY : O R D E R L Y ;
ORGANIZATION : O R G A N I Z A T I O N ;
OTHER : O T H E R ;
OUTPUT : O U T P U T ;
OVERFLOW : O V E R F L O W ;
OVERLINE : O V E R L I N E ;
OWN : O W N ;

PACKED_DECIMAL : P A C K E D '-' D E C I M A L ;
PADDING : P A D D I N G ;
PAGE : P A G E ;
PAGE_COUNTER : P A G E '-' C O U N T E R ;
PARAGRAPH : P A R A G R A P H ;
PARSE : P A R S E ;
PASSWORD : P A S S W O R D ;
PERFORM : P E R F O R M ;
PF : P F ;
PH : P H ;
PIC : P I C ;
PICTURE : P I C T U R E ;
PLUS : P L U S ;
POINTER : P O I N T E R ;
PORT : P O R T ;
POSITION : P O S I T I O N ;
POSITIVE : P O S I T I V E ;
PRINTER : P R I N T E R ;
PRIVATE : P R I V A T E ;
PROCEDURE_POINTER : P R O C E D U R E '-' P O I N T E R ;
PROCEDURES : P R O C E D U R E S ;
PROCEED : P R O C E E D ;
PROCESSING : P R O C E S S I N G ;
PROGRAM : P R O G R A M ;
PROMPT : P R O M P T ;
PURGE : P U R G E ;

QUEUE : Q U E U E ;
QUOTE : Q U O T E ;
QUOTES : Q U O T E S ;

RAISE : R A I S E ;
RAISING : R A I S I N G ;
RANDOM : R A N D O M ;
RD : R D ;
READ : R E A D ;
READER : R E A D E R ;
REAL : R E A L ;
RECEIVE : R E C E I V E ;
RECEIVED : R E C E I V E D ;
RECORD : R E C O R D ;
RECORD_AREA : R E C O R D '-' A R E A ;
RECORDING : R E C O R D I N G ;
RECORDS : R E C O R D S ;
RECURSIVE : R E C U R S I V E ;
REDEFINES : R E D E F I N E S ;
REEL : R E E L ;
REF : R E F ;
REFERENCE : R E F E R E N C E ;
REFERENCES : R E F E R E N C E S ;
RELATIVE : R E L A T I V E ;
RELEASE : R E L E A S E ;
REMAINDER : R E M A I N D E R ;
REMARKS : R E M A R K S ;
REMOTE : R E M O T E ;
REMOVAL : R E M O V A L ;
REMOVE : R E M O V E ;
RENAMES : R E N A M E S ;
REPLACING : R E P L A C I N G ;
REPORTING : R E P O R T I N G ;
REPORTS : R E P O R T S ;
REPOSITORY : R E P O S I T O R Y ;
REQUIRED : R E Q U I R E D ;
RERUN : R E R U N ;
RESERVE : R E S E R V E ;
RESET : R E S E T ;
RESUME : R E S U M E ;
RETURN : R E T U R N ;
RETURN_CODE : R E T U R N '-' C O D E ;
RETURNING : R E T U R N I N G ;
REVERSE_VIDEO : R E V E R S E '-' V I D E O ;
REVERSED : R E V E R S E D ;
REWIND : R E W I N D ;
REWRITE : R E W R I T E ;
RF : R F ;
RH : R H ;
RIGHT : R I G H T ;
ROUNDED : R O U N D E D ;
RUN : R U N ;

SAME : S A M E ;
SAVE : S A V E ;
SD : S D ;
SEARCH : S E A R C H ;
SECURE : S E C U R E ;
SECURITY : S E C U R I T Y ;
SEGMENT : S E G M E N T ;
SEGMENT_LIMIT : S E G M E N T '-' L I M I T ;
SELECT : S E L E C T ;
SELF : S E L F ;
SEND : S E N D ;
SENTENCE : S E N T E N C E ;
SEPARATE : S E P A R A T E ;
SEQUENCE : S E Q U E N C E ;
SEQUENTIAL : S E Q U E N T I A L ;
SET : S E T ;
SHAREDBYALL : S H A R E D B Y A L L ;
SHAREDBYRUNUNIT : S H A R E D B Y R U N U N I T ;
SHARING : S H A R I N G ;
SHIFT_IN : S H I F T '-' I N ;
SHIFT_OUT : S H I F T '-' O U T ;
SHORT : S H O R T ;
SHORT_DATE : S H O R T '-' D A T E ;
SIGN : S I G N ;
SIZE : S I Z E ;
SORT : S O R T ;
SORT_CONTROL : S O R T '-' C O N T R O L ;
SORT_CORE_SIZE : S O R T '-' C O R E '-' S I Z E ;
SORT_FILE_SIZE : S O R T '-' F I L E '-' S I Z E ;
SORT_MERGE : S O R T '-' M E R G E ;
SORT_MESSAGE : S O R T '-' M E S S A G E ;
SORT_MODE_SIZE : S O R T '-' M O D E '-' S I Z E ;
SORT_RETURN : S O R T '-' R E T U R N ;
SOURCE : S O U R C E ;
SOURCE_COMPUTER : S O U R C E '-' C O M P U T E R ;
SPACE : S P A C E ;
SPACES : S P A C E S ;
SPECIAL_NAMES : S P E C I A L '-' N A M E S ;
SQL : S Q L ;
SQLCA : S Q L C A ;
STANDARD : S T A N D A R D ;
STANDARD_1 : S T A N D A R D '-' '1' ;
STANDARD_2 : S T A N D A R D '-' '2' ;
STAT : S T A T ;
START : S T A R T ;
STATEMENT : S T A T E M E N T ;
STATUS : S T A T U S ;
STOP : S T O P ;
STRING : S T R I N G ;
SUB_QUEUE_1 : S U B '-' Q U E U E '-' '1' ;
SUB_QUEUE_2 : S U B '-' Q U E U E '-' '2' ;
SUB_QUEUE_3 : S U B '-' Q U E U E '-' '3' ;
SUBTRACT : S U B T R A C T ;
SUM : S U M ;
SUPER : S U P E R ;
SUPPRESS : S U P P R E S S ;
SYMBOL : S Y M B O L ;
SYMBOLIC : S Y M B O L I C ;
SYNC : S Y N C ;
SYNCHRONIZED : S Y N C H R O N I Z E D ;

TABLE : T A B L E ;
TALLY : T A L L Y ;
TALLYING : T A L L Y I N G ;
TAPE : T A P E ;
TASK : T A S K ;
TERMINAL : T E R M I N A L ;
TERMINATE : T E R M I N A T E ;
TEXT : T E X T ;
THAN : T H A N ;
THEN : T H E N ;
THREAD : T H R E A D ;
THREAD_LOCAL : T H R E A D '-' L O C A L ;
THROUGH : T H R O U G H ;
THRU : T H R U ;
TIME : T I M E ;
TIMER : T I M E R ;
TIMES : T I M E S ;
TIMESTAMP : T I M E S T A M P ;
TIMESTAMP_WITH_TIMEZONE : T I M E S T A M P '-' W I T H '-' T I M E Z O N E ;
TITLE : T I T L E ;
TO : T O ;
TODAYS_DATE : T O D A Y S '-' D A T E ;
TODAYS_NAME : T O D A Y S '-' N A M E ;
TOP : T O P ;
TRAILING : T R A I L I N G ;
TRUE : T R U E ;
TRUNCATED : T R U N C A T E D ;
TYPE : T Y P E ;
TYPEDEF : T Y P E D E F ;

UNDERLINE : U N D E R L I N E ;
UNIT : U N I T ;
UNSTRING : U N S T R I N G ;
UNTIL : U N T I L ;
UP : U P ;
UPON : U P O N ;
USAGE : U S A G E ;
USE : U S E ;
USING : U S I N G ;
UTF_16 : U T F '-' '1' '6' ;
UTF_8 : U T F '-' '8' ;

VALIDATING : V A L I D A T I N G ;
VALUE : V A L U E ;
VALUES : V A L U E S ;
VARYING : V A R Y I N G ;
VIRTUAL : V I R T U A L ;
VOLATILE : V O L A T I L E ;
VL : V L ;

WAIT : W A I T ;
WHEN : W H E N ;
WHEN_COMPILED : W H E N '-' C O M P I L E D ;
WITH : W I T H ;
WORDS : W O R D S ;
WRITE : W R I T E ;

XML : X M L ;

YEAR : Y E A R ;
YYYYDDD : Y Y Y Y D D D ;
YYYYMMDD : Y Y Y Y M M D D ;

ZERO : Z E R O ;
ZERO_FILL : Z E R O '-' F I L L ;
ZEROS : Z E R O S ;
ZEROES : Z E R O E S ;

// Additional tokens for better parsing
CONDITION : C O N D I T I O N ;
ERASE : E R A S E ;
RECORDING_MODE_F : 'F' ;
RECORDING_MODE_V : 'V' ;
RECORDING_MODE_U : 'U' ;
RECORDING_MODE_S : 'S' ;

// FIXED: Enhanced Java type support
JAVA_LONG : 'Long' ;
JAVA_DOUBLE : 'Double' ;
JAVA_FLOAT : 'Float' ;
JAVA_BOOLEAN : 'Boolean' ;
JAVA_BYTE : 'Byte' ;
JAVA_CHAR : 'Char' ;
JAVA_BIG_DECIMAL : 'BigDecimal' ;

// Case-insensitive character fragments for keywords
fragment A : [aA] ;
fragment B : [bB] ;
fragment C : [cC] ;
fragment D : [dD] ;
fragment E : [eE] ;
fragment F : [fF] ;
fragment G : [gG] ;
fragment H : [hH] ;
fragment I : [iI] ;
fragment J : [jJ] ;
fragment K : [kK] ;
fragment L : [lL] ;
fragment M : [mM] ;
fragment N : [nN] ;
fragment O : [oO] ;
fragment P : [pP] ;
fragment Q : [qQ] ;
fragment R : [rR] ;
fragment S : [sS] ;
fragment T : [tT] ;
fragment U : [uU] ;
fragment V : [vV] ;
fragment W : [wW] ;
fragment X : [xX] ;
fragment Y : [yY] ;
fragment Z : [zZ] ;

// Enhanced identifier to handle COBOL naming conventions
// Make this the very last token, to avoid conflict with keywords
IDENTIFIER: [A-Za-z][A-Za-z0-9_-]* ;

