grammar TAL;

// ----------------------
// Top-level Program Structure
// ----------------------
program
    : sourceItem* EOF
    ;

sourceItem
    : namePart
    | globalDeclarationItem
    | blockDeclaration
    | procedureDeclaration
    | directiveLine
    | moduleImport
    | pragmaDirective
    ;

namePart: NAME IDENTIFIER SEMI;

pragmaDirective
    : PRAGMA IDENTIFIER (LPAREN pragmaArgList? RPAREN)? SEMI
    ;
pragmaArgList
    : pragmaArg (COMMA pragmaArg)*
    ;
pragmaArg
    : IDENTIFIER | STRING_LITERAL | INT_LITERAL | INTEGER_VALUE
    ;

// ----------------------
// Global Declarations
// ----------------------
globalDeclarationItem
    : dataDeclaration
    | literalDeclaration
    | defineDeclaration
    | forwardDeclaration
    | externalDeclaration
    | equivalencedVarDeclaration
    | constSection
    | typeSection
    | varSection
    ;

constSection
    : CONST (constDef SEMI)+
    ;
constDef
    : IDENTIFIER ASSIGN expression
    ;

typeSection
    : TYPE (typeDef SEMI)+
    ;
typeDef
    : IDENTIFIER ASSIGN typeSpec
    ;

varSection
    : VAR (varDef SEMI)+
    ;
varDef
    : identList COLON typeSpec (ASSIGN expression)?
    ;

blockDeclaration
    : BLOCK blockName SEMI globalDeclarationItem* END BLOCK SEMI?
    | BLOCK PRIVATE SEMI globalDeclarationItem* END BLOCK SEMI?
    ;

blockName: IDENTIFIER;

// ----------------------
// Data Declarations
// ----------------------
dataDeclaration
    : simpleVariableDeclaration
    | arrayDeclaration
    | structureDeclaration
    | pointerDeclaration
    | readOnlyArrayDeclaration
    | structurePointerDeclaration
    | systemGlobalPointerDeclaration
    | structVariableDeclaration
    | talPointerDeclaration
    ;

talPointerDeclaration
    : typeSpecification PERIOD IDENTIFIER (LBRACK indexRange RBRACK)? (ASSIGN initialization)? (COMMA PERIOD IDENTIFIER (LBRACK indexRange RBRACK)? (ASSIGN initialization)?)* SEMI
    | IDENTIFIER PERIOD IDENTIFIER (LBRACK indexRange RBRACK)? (ASSIGN initialization)? (COMMA PERIOD IDENTIFIER (LBRACK indexRange RBRACK)? (ASSIGN initialization)?)* SEMI
    ;

simpleVariableDeclaration
    : typeSpecification IDENTIFIER (ASSIGN initialization)? (COMMA IDENTIFIER (ASSIGN initialization)?)* SEMI
    ;

arrayDeclaration
    : typeSpecification standardIndirectSymbol? IDENTIFIER LBRACK indexRange RBRACK (ASSIGN initialization)? (COMMA standardIndirectSymbol? IDENTIFIER LBRACK indexRange RBRACK (ASSIGN initialization)?)* SEMI
    ;

structVariableDeclaration
    : STRUCT IDENTIFIER IDENTIFIER SEMI
    | STRUCT IDENTIFIER (PERIOD IDENTIFIER)+ SEMI
    ;

structureDeclaration
    : STRUCT IDENTIFIER (LPAREN MUL RPAREN)? (LBRACK indexRange RBRACK)? SEMI structureBody
    ;

structureBody: BEGIN structureItem* END SEMI?;

structureItem
    : fieldDeclaration
    | nestedStructureDeclaration
    | fillerDeclaration
    | equivalencedFieldDeclaration
    | pointerDeclaration
    | structurePointerDeclaration
    | structPointerFieldDeclaration
    ;

structPointerFieldDeclaration
    : typeSpecification PERIOD IDENTIFIER SEMI
    ;

fieldDeclaration: typeSpecification IDENTIFIER (LBRACK indexRange RBRACK)? (COMMA IDENTIFIER (LBRACK indexRange RBRACK)?)* SEMI;
nestedStructureDeclaration: STRUCT IDENTIFIER (LBRACK indexRange RBRACK)? SEMI structureBody;
fillerDeclaration: FILLER expression SEMI;
equivalencedFieldDeclaration: typeSpecification IDENTIFIER (LBRACK expression RBRACK)? ASSIGN IDENTIFIER SEMI;

pointerDeclaration
    : typeSpecification indirection IDENTIFIER (LBRACK indexRange RBRACK)? (ASSIGN initialization)? (COMMA indirection IDENTIFIER (LBRACK indexRange RBRACK)? (ASSIGN initialization)?)* SEMI
    | typeSpecification MUL IDENTIFIER (LBRACK indexRange RBRACK)? (ASSIGN initialization)? (COMMA MUL IDENTIFIER (LBRACK indexRange RBRACK)? (ASSIGN initialization)?)* SEMI
    ;

structurePointerDeclaration
    : typeSpecification indirection IDENTIFIER LPAREN IDENTIFIER RPAREN (ASSIGN initialization)? (COMMA indirection IDENTIFIER LPAREN IDENTIFIER RPAREN (ASSIGN initialization)?)* SEMI
    ;

systemGlobalPointerDeclaration
    : typeSpecification SGINDIRECT IDENTIFIER (ASSIGN initialization)? (COMMA SGINDIRECT IDENTIFIER (ASSIGN initialization)?)* SEMI
    ;

readOnlyArrayDeclaration
    : typeSpecification IDENTIFIER (LBRACK indexRange RBRACK)? ASSIGN PCONTROL ASSIGN initialization (COMMA IDENTIFIER (LBRACK indexRange RBRACK)? ASSIGN PCONTROL ASSIGN initialization)* SEMI
    ;

equivalencedVarDeclaration
    : typeSpecification IDENTIFIER ASSIGN equivalencedReference (LBRACK expression RBRACK)? offsetSpec? (COMMA IDENTIFIER ASSIGN equivalencedReference (LBRACK expression RBRACK)? offsetSpec?)* SEMI
    ;

equivalencedReference: IDENTIFIER | SGCONTROL | GCONTROL | LCONTROL | SCONTROL;
offsetSpec: (PLUS | MINUS) expression;

literalDeclaration
    : LITERAL IDENTIFIER ASSIGN expression (COMMA IDENTIFIER ASSIGN expression)* SEMI
    ;

defineDeclaration
    : DEFINE IDENTIFIER ASSIGN expression SEMI HASH?
    ;

// ----------------------
// Type System
// ----------------------
typeSpec
    : baseType                        #baseTypeSpec
    | arrayType                       #arrayTypeSpec
    ;

typeSpecification
    : dataType
    | forwardTypeName
    ;

baseType
    : simpleType
    | IDENTIFIER
    | stringType
    | recordType
    | pointerType
    | LPAREN typeSpec RPAREN
    ;

simpleType
    : INT
    | UINT
    | SHORT
    | USHORT
    | LONG
    | ULONG
    | BOOL
    | CHAR
    | BYTE
    ;

pointerType
    : REF typeSpec
    | BXOR typeSpec
    ;

arrayType
    : baseType LBRACK expression? RBRACK
    ;

stringType
    : STRING (LBRACK expression RBRACK)?
    ;

recordType
    : RECORD fieldDecl+ END
    ;
fieldDecl
    : identList COLON typeSpec SEMI
    ;

dataType
    : STRING
    | STRING LPAREN INTEGER_VALUE RPAREN
    | INT | INT32 | INT64
    | FIXED fixedPointSpec?
    | REAL | REAL64
    | UNSIGNED LPAREN (INT_LITERAL | INTEGER_VALUE | TAL_LIT_BINARY | TAL_LIT_OCTAL | TAL_LIT_HEX) RPAREN
    | BYTE | CHAR | TIMESTAMP | EXTADDR | SGADDR
    ;

fixedPointSpec: LPAREN (PLUS | MINUS)? (INT_LITERAL | INTEGER_VALUE | TAL_LIT_BINARY | TAL_LIT_OCTAL | TAL_LIT_HEX) RPAREN;

forwardTypeName: IDENTIFIER;
indirection: PERIOD | EXTINDIRECT | SGINDIRECT;
structureReferral: LPAREN IDENTIFIER RPAREN;
indexRange: lowerBound COLON upperBound;
lowerBound: expression;
upperBound: expression;

initialization: expression | constantList;
constantList: (repetitionFactor MUL)? LBRACK constantListItem (COMMA constantListItem)* RBRACK;
constantListItem: constantExpr | STRING_LITERAL;
repetitionFactor: expression;

identList
    : IDENTIFIER (COMMA IDENTIFIER)*
    ;

// ----------------------
// Procedures
// ----------------------
procedureDeclaration
    : procHeader procBody SEMI?
    | procHeader SEMI
    ;

procHeader
    : typedProcHeader
    | untypedProcHeader
    ;

typedProcHeader: typeSpecification PROC procName formalParamList? procAttributeList? SEMI;
untypedProcHeader: (PROC | SUBPROC) procName formalParamList? procAttributeList? SEMI;

procName: IDENTIFIER;

formalParamList: LPAREN formalParam (COMMA formalParam)* RPAREN;

formalParam
    : dataType MUL IDENTIFIER
    | dataType indirection? IDENTIFIER structureReferral?
    | STRUCT IDENTIFIER IDENTIFIER
    | forwardTypeName MUL IDENTIFIER
    | forwardTypeName indirection IDENTIFIER structureReferral?
    | forwardTypeName IDENTIFIER structureReferral?
    | typeSpecification IDENTIFIER
    | IDENTIFIER
    | (VAR | REF)? identList COLON typeSpec
    ;

procAttributeList: procAttribute (COMMA procAttribute)*;

procAttribute
    : MAIN
    | INTERRUPT
    | RESIDENT
    | CALLABLE
    | PRIV
    | EXTENSIBLE extensibleParamCount?
    | VARIABLE
    ;

extensibleParamCount: LBRACE INTEGER_VALUE RBRACE;

procBody
    : (declarationOrStatement)*
      BEGIN
      (localDeclarationStatement | statement | entryPointDeclaration)*
      END SEMI?
    | FORWARD SEMI
    | EXTERNAL SEMI
    ;

declarationOrStatement
    : globalDeclarationItem
    | labelDeclaration
    | entryPointDeclaration
    | subprocedureDeclaration
    | forwardSubprocedureDeclaration
    ;

subprocedureDeclaration: SUBPROC procName formalParamList? SEMI procBody;
entryPointDeclaration: ENTRY IDENTIFIER SEMI;
labelDeclaration: LABEL IDENTIFIER (COMMA IDENTIFIER)* SEMI;
forwardSubprocedureDeclaration: SUBPROC procName formalParamList? SEMI FORWARD SEMI;

// ----------------------
// Forward and External Declarations
// ----------------------
forwardDeclaration
    : FORWARD PROC procName formalParamList? SEMI
    | FORWARD STRUCT IDENTIFIER SEMI
    | FORWARD typeDeclaration SEMI
    ;

typeDeclaration: dataType IDENTIFIER | forwardTypeName IDENTIFIER;

externalDeclaration
    : EXTERNAL PROC IDENTIFIER languageSpecifier? SEMI
    | EXTERNAL STRUCT IDENTIFIER languageSpecifier? SEMI
    | EXTERNAL identList (COLON typeSpec)? SEMI
    ;

languageSpecifier: LANGUAGE languageNameChoice;
languageNameChoice: IDENTIFIER | COBOL85 | FORTRAN | PASCAL | UNSPECIFIED;

// ----------------------
// Module Import
// ----------------------
moduleImport: IMPORT moduleIdentifier SEMI | IMPORT moduleIdentifier LPAREN importedItems RPAREN SEMI;
moduleIdentifier: IDENTIFIER (PERIOD IDENTIFIER)*;
importedItems: IDENTIFIER (COMMA IDENTIFIER)* | MUL;

// ----------------------
// Statements
// ----------------------
statement
    : assignmentStatement                            #assignStmt
    | localDeclarationStatement                      #localDeclStmt
    | bitDepositStatement                            #bitDepositStmt
    | bitFieldAssignmentStatement SEMI               #bitFieldAssignStmt
    | pointerAssignmentStatement SEMI                #pointerAssignStmt
    | pointerDereferenceStatement SEMI               #pointerDerefStmt
    | stringMoveStatement SEMI                       #stringMoveStmt
    | moveStatement SEMI                             #moveStmt
    | scanStatement SEMI                             #scanStmt
    | rscanStatement SEMI                            #rscanStmt
    | callStatement SEMI                             #callStmt
    | ifStatement                                    #ifStmt
    | caseStatement                                  #caseStmt
    | whileStatement                                 #whileStmt
    | doUntilStatement SEMI                          #doUntilStmt
    | forStatement                                   #forStmt
    | gotoStatement SEMI                             #gotoStmt
    | returnStatement SEMI                           #returnStmt
    | assertStatement SEMI                           #assertStmt
    | useStatement SEMI                              #useStmt
    | dropStatement SEMI                             #dropStmt
    | stackStatement SEMI                            #stackStmt
    | storeStatement SEMI                            #storeStmt
    | codeStatement SEMI                             #codeStmt
    | labeledStatement                               #labeledStmt
    | expressionStatement SEMI                       #exprStmt
    | blockStatement                                 #nestedBlockStmt
    | SEMI                                           #emptyStmt
    | block                                          #blockStmt
    | varSection                                     #localVarSection
    | constSection                                   #localConstSection
    | typeSection                                    #localTypeSection
    ;

assignmentStatement
    : variableExpr ASSIGN expression              #simpleAssign
    ;

expressionStatement
    : expression                                  #exprOnly
    ;

blockStatement
    : BEGIN statement* END                        #nestedBlock
    ;

block
    : BEGIN statement* END SEMI?                  #simpleBlock
    ;

bitFieldAssignmentStatement
    : variableExpr BITFIELDSTART bitPosition (COLON bitPosition)? GT ASSIGN expression
    ;

pointerAssignmentStatement
    : ADDRESS variableExpr ASSIGN ADDRESS variableExpr
    | variableExpr ASSIGN ADDRESS variableExpr
    | ADDRESS variableExpr ASSIGN variableExpr
    ;

pointerDereferenceStatement
    : PERIOD variableExpr ASSIGN expression
    ;

stringMoveStatement
    : variableExpr STRINGMOVE expression
    ;

moveStatement
    : MOVE variableExpr TO variableExpr
    ;

bitDepositStatement
    : BITDEPOSIT expression TO variableExpr BITFIELDSTART bitPosition (COLON bitPosition)? GT SEMI
    ;

scanStatement
    : SCAN scanObject WHILE scanTerminator TO nextAddr
    ;

rscanStatement
    : RSCAN scanObject WHILE scanTerminator TO nextAddr
    ;

scanObject: variableExpr;
scanTerminator: expression;
nextAddr: expression;
bitPosition: expression;

localDeclarationStatement
    : constSection
    | typeSection
    | varSection
    | labelDeclaration
    ;

ifStatement
    : IF expression THEN statementSequence (ELSE statementSequence)? ENDIF SEMI
    ;

caseStatement
    : CASE expression OF BEGIN caseArm* otherwiseArm? END SEMI
    ;

otherwiseArm: OTHERWISE COLON statement;
statementSequence: statement*;
otherwiseStatement: OTHERWISE COLON statementSequence;
caseArm: caseLabelList COLON statement;
caseLabelList: caseLabel (COMMA caseLabel)*;
caseLabel: INT_LITERAL | CHAR_LITERAL | STRING_LITERAL;

whileStatement
    : WHILE expression DO BEGIN statement* END SEMI?
    | WHILE expression DO statement (END SEMI?)?
    ;

doUntilStatement: DO statementSequence UNTIL expression;
doWhileStmt: DO statement WHILE expression (END SEMI?)? ;

forStatement
    : FOR IDENTIFIER ASSIGN initialValue direction limitValue (BY stepValue)? DO statementSequence ENDFOR SEMI?
    ;
initialValue: expression;
direction: TO | DOWNTO;
limitValue: expression;
stepValue: expression;

// Procedure Calls
callStatement
    : CALL? (procedureNameCall | preprocessedSystemFunctionCall) (LPAREN callParameters? RPAREN)?
    | CALL? qualifiedName LPAREN argList? RPAREN
    ;

preprocessedSystemFunctionCall
    : SYSFUNCSTRING
    | SYSFUNCPARAM
    | SYSFUNCDISPLAY
    | SYSFUNCWRITE
    | SYSFUNCREAD
    | SYSFUNCUPSHIFT
    | SYSFUNCDOWNSHIFT
    ;

procedureNameCall: IDENTIFIER;

callParameters: callParameter (COMMA callParameter)*;
callParameter: expression | IDENTIFIER | MUL | fileIdentifierExpr;
argList: expression (COMMA expression)*;

fileIdentifierExpr: DOLLAR IDENTIFIER | DOLLAR (INT_LITERAL | INTEGER_VALUE | TAL_LIT_BINARY | TAL_LIT_OCTAL | TAL_LIT_HEX) | IDENTIFIER;

// Other Statements
gotoStatement: GOTO IDENTIFIER;
returnStatement
    : RETURN expression? SEMI
    ;

assertStatement: ASSERT assertLevel? expression;
useStatement: USE IDENTIFIER (COMMA IDENTIFIER)*;
dropStatement: DROP IDENTIFIER (COMMA IDENTIFIER)*;
stackStatement: STACK expression (COMMA expression)*;
storeStatement: STORE variableExpr (COMMA variableExpr)*;
codeStatement: CODE LPAREN machineCode RPAREN;

assertLevel: (INT_LITERAL | INTEGER_VALUE | TAL_LIT_BINARY | TAL_LIT_OCTAL | TAL_LIT_HEX) COLON;

machineCode: (machineMnemonic (machineOperand (COMMA machineOperand)*)? SEMI?)+;
machineMnemonic: IDENTIFIER | CON | FULL;
machineOperand: (INT_LITERAL | INTEGER_VALUE | TAL_LIT_BINARY | TAL_LIT_OCTAL | TAL_LIT_HEX) | IDENTIFIER | ADDRESS IDENTIFIER | PERIOD IDENTIFIER | STRING_LITERAL;

labeledStatement: IDENTIFIER COLON statement;

// ----------------------
// Compiler Directives
// ----------------------
directiveLine
    : DIRECTIVE sourceDirective SEMI
    | DIRECTIVE listingDirective SEMI
    | DIRECTIVE pageDirective SEMI
    | DIRECTIVE sectionDirective SEMI
    | DIRECTIVE ifDirective
    | DIRECTIVE compilerOptionDirective SEMI
    | DIRECTIVE precompiledHeaderImport
    | DIRECTIVE SYMBOLS SEMI
    | DIRECTIVE IDENTIFIER SEMI
    | DIRECTIVE directiveArgument (COMMA directiveArgument)* (LPAREN directiveArgumentList RPAREN)? SEMI
    ;

sourceDirective: SOURCE ((ASSIGN | COMMA)? STRING_LITERAL | (ASSIGN | COMMA)? IDENTIFIER (LPAREN IDENTIFIER (COMMA IDENTIFIER)* RPAREN)? | INCLUDE STRING_LITERAL);
listingDirective: LIST | NOLIST;
pageDirective: PAGE STRING_LITERAL?;
sectionDirective: SECTION IDENTIFIER?;
ifDirective: IF directiveExpression SEMI | IFNOT directiveExpression SEMI | ENDIF SEMI;
directiveExpression: IDENTIFIER (ASSIGN | NEQ) (STRING_LITERAL | INT_LITERAL | INTEGER_VALUE | TAL_LIT_BINARY | TAL_LIT_OCTAL | TAL_LIT_HEX | IDENTIFIER) | IDENTIFIER;
compilerOptionDirective: COMPACT | CHECK | INSPECT | SYMBOLS | NOLMAP | HIGHPIN | HIGHREQUESTERS;
precompiledHeaderImport: PCH STRING_LITERAL SEMI;
directiveArgument: IDENTIFIER | INT_LITERAL | INTEGER_VALUE | STRING_LITERAL | TAL_LIT_BINARY | TAL_LIT_OCTAL | TAL_LIT_HEX;
directiveArgumentList: directiveArgument (COMMA directiveArgument)*;

// ----------------------
// Expressions
// ----------------------
expression: assignmentExpr;
assignmentExpr: logicalOrExpr (ASSIGN assignmentExpr)?;

logicalOrExpr
    : logicalAndExpr (OR logicalAndExpr)*
    | exprOr
    ;
logicalAndExpr
    : equalityExpr (AND equalityExpr)*
    | exprAnd
    ;

exprOr: exprAnd (OR exprAnd)*;
exprAnd: exprBitOr (AND exprBitOr)*;
exprBitOr: exprBitXor (BOR exprBitXor)*;
exprBitXor: exprBitAnd (BXOR exprBitAnd)*;
exprBitAnd: exprEq (BAND exprEq)*;
exprEq: exprRel ((EQ | NEQ) exprRel)*;
exprRel: exprShift ((LT | LE | GT | GE) exprShift)*;
exprShift: exprAdd ((SHL | SHR) exprAdd)*;
exprAdd: exprMul ((PLUS | MINUS) exprMul)*;
exprMul: exprUnary ((MUL | DIV | MOD) exprUnary)*;
exprUnary: (NOT | MINUS | PLUS | BAND | BOR | BXOR | ADDRESS)? exprPrimary;

equalityExpr: relationalExpr ((ASSIGN | NEQ) relationalExpr)*;
relationalExpr: shiftExpr ((LT | GT | LE | GE) shiftExpr)*;
shiftExpr: additiveExpr ((SHL | SHR) additiveExpr)*;
additiveExpr: multiplicativeExpr ((PLUS | MINUS) multiplicativeExpr)*;
multiplicativeExpr: unaryExpr ((MUL | DIV | MOD) unaryExpr)*;
unaryExpr: (PLUS | MINUS | NOT | ADDRESS)? primaryExpr;

primaryExpr
    : constantExpr
    | variableExpr
    | functionCall
    | LPAREN expression RPAREN
    ;

exprPrimary
    : LPAREN expression RPAREN
    | literal
    | qualifiedName
        (   LPAREN argList? RPAREN
        |   LBRACK expression RBRACK
        |   PERIOD IDENTIFIER
        )*
    ;

functionCall
    : preprocessedSystemFunctionCall LPAREN callParameters? RPAREN
    | IDENTIFIER LPAREN parameterList? RPAREN
    ;

constantExpr
    : INT_LITERAL | FIXED_LITERAL | REAL_LITERAL | STRING_LITERAL
    | IDENTIFIER
    | INTEGER_VALUE
    | TAL_LIT_BINARY
    | TAL_LIT_OCTAL
    | TAL_LIT_HEX
    | NIL
    ;

variableExpr
    : IDENTIFIER (arrayRef | memberAccess | bitField | functionArgs)*
    | standardIndirectSymbol IDENTIFIER (arrayRef | memberAccess | bitField | functionArgs)*
    | ADDRESS IDENTIFIER (arrayRef | memberAccess | bitField | functionArgs)*
    | systemGlobalAccess
    | guardianFileName
    ;

arrayRef: LBRACK expression RBRACK;
memberAccess: PERIOD IDENTIFIER;
bitField: BITFIELDSTART expression (COLON expression)? GT;
functionArgs: LPAREN parameterList? RPAREN;

guardianFileName: DOLLAR IDENTIFIER (PERIOD IDENTIFIER)*;
systemGlobalAccess: DOLLAR IDENTIFIER;
standardIndirectSymbol: PERIOD;

parameterList: parameter (COMMA parameter)* | MUL;
parameter: expression | IDENTIFIER | MUL;

qualifiedName
    : IDENTIFIER (PERIOD IDENTIFIER)*
    ;

literal
    : INT_LITERAL
    | CHAR_LITERAL
    | STRING_LITERAL
    | TRUE
    | FALSE
    | NIL
    ;

// ----------------------
// LEXER RULES
// ----------------------

// ----------------------
// LEXER RULES
// ----------------------

// TAL-specific preprocessed tokens (when using preprocessor)
SYSFUNCSTRING     : '__TAL_SYS_FUNC_STRING__';
SYSFUNCPARAM      : '__TAL_SYS_FUNC_PARAM__';
SYSFUNCDISPLAY    : '__TAL_SYS_FUNC_DISPLAY__';
SYSFUNCWRITE      : '__TAL_SYS_FUNC_WRITE__';
SYSFUNCREAD       : '__TAL_SYS_FUNC_READ__';
SYSFUNCUPSHIFT    : '__TAL_SYS_FUNC_UPSHIFT__';
SYSFUNCDOWNSHIFT  : '__TAL_SYS_FUNC_DOWNSHIFT__';

STRINGASSIGN      : '__TAL_OP_STRING_ASSIGN__';
STRINGMOVE        : '\':=\'';                    // TAL string move operator
BITFIELDSTART     : '__TAL_OP_BIT_FIELD_START__';
EXTINDIRECT       : '__TAL_OP_EXT_INDIRECT__';
SGINDIRECT        : '__TAL_OP_SG_INDIRECT__';
ARROW             : '__TAL_OP_ARROW__' | '->';
MOVEREVASSIGN     : '__TAL_MOVE_REV_ASSIGN_OP__';

TAL_LIT_BINARY    : '__TAL_LIT_BINARY_' DIGIT_BIN+;
TAL_LIT_OCTAL     : '__TAL_LIT_OCTAL_' [0-7]+;
TAL_LIT_HEX       : '__TAL_LIT_HEX_' DIGIT_HEX+;

// Keywords - TAL specific
AWAITIO     : 'AWAITIO';
ASSERT      : 'ASSERT';
BLOCK       : 'BLOCK';
BY          : 'BY';
CALLABLE    : 'CALLABLE';
CHECK       : 'CHECK';
CLOSE       : 'CLOSE';
CODE        : 'CODE';
COMPACT     : 'COMPACT';
COBOL85     : 'COBOL85';
CON         : 'CON';
DEFINE      : 'DEFINE';
DOWNTO      : 'DOWNTO';
DROP        : 'DROP';
ENDFOR      : 'ENDFOR';
ENDIF       : 'ENDIF';
ENTRY       : 'ENTRY';
EXTADDR     : 'EXTADDR';
EXTENSIBLE  : 'EXTENSIBLE';
FILEINFO    : 'FILEINFO';
FILLER      : 'FILLER';
FIXED       : 'FIXED';
FORTRAN     : 'FORTRAN';
FULL        : 'FULL';
GOTO        : 'GOTO';
HIGHPIN     : 'HIGHPIN';
HIGHREQUESTERS : 'HIGHREQUESTERS';
IFNOT       : 'IFNOT';
INCLUDE     : 'INCLUDE';
IMPORT      : 'IMPORT';
INSPECT     : 'INSPECT';
INTERRUPT   : 'INTERRUPT';
INT32       : 'INT(32)';
INT64       : 'INT(64)';
LABEL       : 'LABEL';
LANGUAGE    : 'LANGUAGE';
LIST        : 'LIST';
LITERAL     : 'LITERAL';
MAIN        : 'MAIN';
NAME        : 'NAME';
NIL         : 'NIL';
NOLIST      : 'NOLIST';
NOLMAP      : 'NOLMAP';
OPEN        : 'OPEN';
OTHERWISE   : 'OTHERWISE';
PAGE        : 'PAGE';
PASCAL      : 'PASCAL';
PCH         : 'PCH';
PRAGMA      : 'PRAGMA';
PRIVATE     : 'PRIVATE';
PRIV        : 'PRIV';
PROC        : 'PROC';
PROCESSCREATE : 'PROCESS_CREATE';
READX       : 'READX';
REAL        : 'REAL';
REAL64      : 'REAL(64)';
RESIDENT    : 'RESIDENT';
RSCAN       : 'RSCAN';
SCAN        : 'SCAN';
SECTION     : 'SECTION';
SGADDR      : 'SGADDR';
SOURCE      : 'SOURCE';
STACK       : 'STACK';
STORE       : 'STORE';
STRUCT      : 'STRUCT';
SUBPROC     : 'SUBPROC';
SYMBOLS     : 'SYMBOLS';
TIMESTAMP   : 'TIMESTAMP';
TIME        : 'TIME';
UNSPECIFIED : 'UNSPECIFIED';
UNSIGNED    : 'UNSIGNED';
USE         : 'USE';
WRITEX      : 'WRITEX';
MOVE        : 'MOVE';        // Added for moveStatement
BITDEPOSIT  : 'BITDEPOSIT';  // Added for bitDepositStatement

// Keywords - Common language constructs
PROCEDURE   : 'PROCEDURE';
RETURNS     : 'RETURNS';
OPTIONS     : 'OPTIONS';
EXTERNAL    : 'EXTERNAL';
CONST       : 'CONST';
TYPE        : 'TYPE';
VAR         : 'VAR';
RECORD      : 'RECORD';
BEGIN       : 'BEGIN';
END         : 'END';
IF          : 'IF';
THEN        : 'THEN';
ELSE        : 'ELSE';
CASE        : 'CASE';
OF          : 'OF';
WHILE       : 'WHILE';
DO          : 'DO';
FOR         : 'FOR';
TO          : 'TO';
UNTIL       : 'UNTIL';
RETURN      : 'RETURN';
CALL        : 'CALL';
REF         : 'REF';
STRING      : 'STRING';
FORWARD     : 'FORWARD';
VARIABLE    : 'VARIABLE';


// Data types
INT         : 'INT';
UINT        : 'UINT';
SHORT       : 'SHORT';
USHORT      : 'USHORT';
LONG        : 'LONG';
ULONG       : 'ULONG';
BOOL        : 'BOOL';
CHAR        : 'CHAR';
BYTE        : 'BYTE';

// Boolean literals
TRUE        : 'TRUE';
FALSE       : 'FALSE';

// Control tokens
PCONTROL    : '\'' 'P' '\'';
SGCONTROL   : '\'' 'SG' '\'';
GCONTROL    : '\'' 'G' '\'';
LCONTROL    : '\'' 'L' '\'';
SCONTROL    : '\'' 'S' '\'';

// Operators
ASSIGN      : ':=' | '=';
PLUS        : '+';
MINUS       : '-';
MUL         : '*';
DIV         : '/';
MOD         : 'MOD' | '%';

EQ          : '==';
NEQ         : '<>' | '!=' | 'NEQ';

LT          : '<';
LE          : '<=';
GT          : '>';
GE          : '>=';

SHL         : 'SHL' | '<<';
SHR         : 'SHR' | '>>';

AND         : 'AND' | '&&';
OR          : 'OR' | '||';
NOT         : 'NOT' | '!';
BAND        : '&';
BOR         : '|';
BXOR        : '^';

// Delimiters
DOLLAR      : '$';
LPAREN      : '(';
RPAREN      : ')';
LBRACK      : '[';
RBRACK      : ']';
LBRACE      : '{';
RBRACE      : '}';
COMMA       : ',';
COLON       : ':';
SEMI        : ';';
PERIOD      : '.';
HASH        : '#';
DIRECTIVE   : '?';
ADDRESS     : '@';

// Literals
INTEGER_VALUE   : DIGIT+;
INT_LITERAL     : ('%' [0-7]+)
                | ('%' [Xx] DIGIT_HEX+)
                | ('%' [Bb] DIGIT_BIN+)
                | (DIGIT+ 'D')
                | '0' | [1-9][0-9]* | '0'[xX][0-9a-fA-F]+
                ;
FIXED_LITERAL   : DIGIT+ (PERIOD DIGIT+)? 'F' | '%' [Xx] DIGIT_HEX+ 'F';
REAL_LITERAL    : (DIGIT+ PERIOD DIGIT* | PERIOD DIGIT+ | DIGIT+) ([Ee] [+-]? DIGIT+) | DIGIT+ 'L';
CHAR_LITERAL    : '\'' (~['\\\r\n] | '\\' .) '\'';
STRING_LITERAL  : '"' (~["\\\r\n] | '\\' . | '""')* '"';

// Identifiers
IDENTIFIER      : LETTER (LETTER | DIGIT)*;

// Fragment rules
fragment DIGIT      : [0-9];
fragment DIGIT_HEX  : [0-9a-fA-F];
fragment DIGIT_BIN  : [01];
fragment LETTER     : [a-zA-Z_];

// Comments and Whitespace
DOC_COMMENT     : '!*' .*? '*!' -> channel(HIDDEN);
COMMENT         : ('!' | '--') ~[\r\n]* -> skip;
LINE_COMMENT    : '//' ~[\r\n]* -> skip;
WS              : [ \t\r\n\f]+ -> skip;

// Error handling
ERROR           : .;
