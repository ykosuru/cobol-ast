
import java.util.*;
import java.io.*;

/**
 * Complete implementation of data item collection for all COBOL statements
 * This analyzes all statements to extract referenced data items for complexity analysis
 */

public class Util
{
    public static void collectReferencedDataItems(CobolParser.SentenceContext ctx, Set<String> referencedDataItems) {
        for (CobolParser.StatementContext stmtCtx : ctx.statement()) {
            collectFromStatement(stmtCtx, referencedDataItems);
        }
    }

    public static void collectFromStatement(CobolParser.StatementContext stmtCtx, Set<String> referencedDataItems) {
        // ACCEPT statement
        if (stmtCtx.acceptStatement() != null) {
            if (stmtCtx.acceptStatement().identifier() != null) {
                referencedDataItems.add(stmtCtx.acceptStatement().identifier().getText());
            }
        }
        
        // ADD statement
        if (stmtCtx.addStatement() != null) {
            CobolParser.AddStatementContext addStmt = stmtCtx.addStatement();
            
            // ADD TO format
            if (addStmt.addToStatement() != null) {
                CobolParser.AddToStatementContext addCtx = addStmt.addToStatement();
                for (CobolParser.AddFromContext fromCtx : addCtx.addFrom()) {
                    if (fromCtx.identifier() != null) {
                        referencedDataItems.add(fromCtx.identifier().getText());
                    }
                }
                for (CobolParser.AddToContext toCtx : addCtx.addTo()) {
                    if (toCtx.identifier() != null) {
                        referencedDataItems.add(toCtx.identifier().getText());
                    }
                }
            }
            
            // ADD GIVING format
            if (addStmt.addToGivingStatement() != null) {
                CobolParser.AddToGivingStatementContext givingCtx = addStmt.addToGivingStatement();
                for (CobolParser.AddFromContext fromCtx : givingCtx.addFrom()) {
                    if (fromCtx.identifier() != null) {
                        referencedDataItems.add(fromCtx.identifier().getText());
                    }
                }
                for (CobolParser.AddToGivingContext toGivingCtx : givingCtx.addToGiving()) {
                    if (toGivingCtx.identifier() != null) {
                        referencedDataItems.add(toGivingCtx.identifier().getText());
                    }
                }
                for (CobolParser.AddGivingContext givingTargetCtx : givingCtx.addGiving()) {
                    if (givingTargetCtx.identifier() != null) {
                        referencedDataItems.add(givingTargetCtx.identifier().getText());
                    }
                }
            }
            
            // ADD CORRESPONDING format
            if (addStmt.addCorrespondingStatement() != null) {
                CobolParser.AddCorrespondingStatementContext corrCtx = addStmt.addCorrespondingStatement();
                if (corrCtx.identifier() != null) {
                    referencedDataItems.add(corrCtx.identifier().getText());
                }
                if (corrCtx.addTo() != null && corrCtx.addTo().identifier() != null) {
                    referencedDataItems.add(corrCtx.addTo().identifier().getText());
                }
            }
        }
        
        // ALTER statement
        if (stmtCtx.alterStatement() != null) {
            for (CobolParser.AlterProceedToContext alterCtx : stmtCtx.alterStatement().alterProceedTo()) {
                // ALTER doesn't typically reference data items, but procedure names
                // We could collect procedure references here if needed
            }
        }
        
        // ALLOCATE statement
        if (stmtCtx.allocateStatement() != null) {
            CobolParser.AllocateStatementContext allocCtx = stmtCtx.allocateStatement();
            if (allocCtx.identifier() != null && allocCtx.identifier().size() > 0) {
                // First identifier is size, second is the target variable
                if (allocCtx.identifier().size() > 1) {
                    referencedDataItems.add(allocCtx.identifier(1).getText());
                }
            }
        }
        
        // CALL statement
        if (stmtCtx.callStatement() != null) {
            CobolParser.CallStatementContext callCtx = stmtCtx.callStatement();
            
            // Program name (if identifier)
            if (callCtx.identifier() != null) {
                referencedDataItems.add(callCtx.identifier().getText());
            }
            
            // USING parameters
            if (callCtx.callUsingPhrase() != null) {
                for (CobolParser.CallUsingParameterContext paramCtx : callCtx.callUsingPhrase().callUsingParameter()) {
                    if (paramCtx.callByReferencePhrase() != null) {
                        for (CobolParser.CallByReferenceContext refCtx : paramCtx.callByReferencePhrase().callByReference()) {
                            if (refCtx.identifier() != null) {
                                referencedDataItems.add(refCtx.identifier().getText());
                            }
                        }
                    }
                    if (paramCtx.callByValuePhrase() != null) {
                        for (CobolParser.CallByValueContext valCtx : paramCtx.callByValuePhrase().callByValue()) {
                            if (valCtx.identifier() != null) {
                                referencedDataItems.add(valCtx.identifier().getText());
                            }
                        }
                    }
                    if (paramCtx.callByContentPhrase() != null) {
                        for (CobolParser.CallByContentContext contCtx : paramCtx.callByContentPhrase().callByContent()) {
                            if (contCtx.identifier() != null) {
                                referencedDataItems.add(contCtx.identifier().getText());
                            }
                        }
                    }
                }
            }
            
            // GIVING parameter
            if (callCtx.callGivingPhrase() != null && callCtx.callGivingPhrase().identifier() != null) {
                referencedDataItems.add(callCtx.callGivingPhrase().identifier().getText());
            }
        }
        
        // CANCEL statement
        if (stmtCtx.cancelStatement() != null) {
            for (CobolParser.CancelCallContext cancelCtx : stmtCtx.cancelStatement().cancelCall()) {
                if (cancelCtx.identifier() != null) {
                    referencedDataItems.add(cancelCtx.identifier().getText());
                }
            }
        }
        
        // CLOSE statement
        if (stmtCtx.closeStatement() != null) {
            for (CobolParser.CloseFileContext fileCtx : stmtCtx.closeStatement().closeFile()) {
                if (fileCtx.fileName() != null) {
                    referencedDataItems.add(fileCtx.fileName().getText());
                }
            }
        }
        
        // COMPUTE statement
        if (stmtCtx.computeStatement() != null) {
            CobolParser.ComputeStatementContext compCtx = stmtCtx.computeStatement();
            
            // Target variables
            for (CobolParser.ComputeStoreContext storeCtx : compCtx.computeStore()) {
                if (storeCtx.identifier() != null) {
                    referencedDataItems.add(storeCtx.identifier().getText());
                }
            }
            
            // Expression variables (simplified - would need full expression parsing for complete analysis)
            if (compCtx.arithmeticExpression() != null) {
                collectFromArithmeticExpression(compCtx.arithmeticExpression(), referencedDataItems);
            }
        }
        
        // CONTINUE statement - no data items to collect
        
        // DELETE statement
        if (stmtCtx.deleteStatement() != null) {
            if (stmtCtx.deleteStatement().fileName() != null) {
                referencedDataItems.add(stmtCtx.deleteStatement().fileName().getText());
            }
        }
        
        // DISABLE statement
        if (stmtCtx.disableStatement() != null) {
            CobolParser.DisableStatementContext disCtx = stmtCtx.disableStatement();
            if (disCtx.cdName() != null) {
                referencedDataItems.add(disCtx.cdName().getText());
            }
            if (disCtx.identifier() != null) {
                referencedDataItems.add(disCtx.identifier().getText());
            }
        }
        
        // DISPLAY statement
        if (stmtCtx.displayStatement() != null) {
            for (CobolParser.DisplayOperandContext operandCtx : stmtCtx.displayStatement().displayOperand()) {
                if (operandCtx.identifier() != null) {
                    referencedDataItems.add(operandCtx.identifier().getText());
                }
            }
            
            // UPON clause
            if (stmtCtx.displayStatement().displayUpon() != null) {
                if (stmtCtx.displayStatement().displayUpon().mnemonicName() != null) {
                    referencedDataItems.add(stmtCtx.displayStatement().displayUpon().mnemonicName().getText());
                }
            }
        }
        
        // DIVIDE statement
        if (stmtCtx.divideStatement() != null) {
            CobolParser.DivideStatementContext divCtx = stmtCtx.divideStatement();
            
            // Source operand
            if (divCtx.identifier() != null) {
                referencedDataItems.add(divCtx.identifier().getText());
            }
            
            // INTO format
            if (divCtx.divideIntoStatement() != null) {
                for (CobolParser.DivideIntoContext intoCtx : divCtx.divideIntoStatement().divideInto()) {
                    if (intoCtx.identifier() != null) {
                        referencedDataItems.add(intoCtx.identifier().getText());
                    }
                }
            }
            
            // INTO GIVING format
            if (divCtx.divideIntoGivingStatement() != null) {
                CobolParser.DivideIntoGivingStatementContext intoGivingCtx = divCtx.divideIntoGivingStatement();
                if (intoGivingCtx.identifier() != null) {
                    referencedDataItems.add(intoGivingCtx.identifier().getText());
                }
                if (intoGivingCtx.divideGivingPhrase() != null) {
                    for (CobolParser.DivideGivingContext givingCtx : intoGivingCtx.divideGivingPhrase().divideGiving()) {
                        if (givingCtx.identifier() != null) {
                            referencedDataItems.add(givingCtx.identifier().getText());
                        }
                    }
                }
            }
            
            // BY GIVING format
            if (divCtx.divideByGivingStatement() != null) {
                CobolParser.DivideByGivingStatementContext byGivingCtx = divCtx.divideByGivingStatement();
                if (byGivingCtx.identifier() != null) {
                    referencedDataItems.add(byGivingCtx.identifier().getText());
                }
                if (byGivingCtx.divideGivingPhrase() != null) {
                    for (CobolParser.DivideGivingContext givingCtx : byGivingCtx.divideGivingPhrase().divideGiving()) {
                        if (givingCtx.identifier() != null) {
                            referencedDataItems.add(givingCtx.identifier().getText());
                        }
                    }
                }
            }
            
            // REMAINDER clause
            if (divCtx.divideRemainder() != null && divCtx.divideRemainder().identifier() != null) {
                referencedDataItems.add(divCtx.divideRemainder().identifier().getText());
            }
        }
        
        // ENABLE statement
        if (stmtCtx.enableStatement() != null) {
            CobolParser.EnableStatementContext enCtx = stmtCtx.enableStatement();
            if (enCtx.cdName() != null) {
                referencedDataItems.add(enCtx.cdName().getText());
            }
            if (enCtx.identifier() != null) {
                referencedDataItems.add(enCtx.identifier().getText());
            }
        }
        
        // ENTRY statement
        if (stmtCtx.entryStatement() != null) {
            for (CobolParser.IdentifierContext idCtx : stmtCtx.entryStatement().identifier()) {
                referencedDataItems.add(idCtx.getText());
            }
        }
        
        // EVALUATE statement
        if (stmtCtx.evaluateStatement() != null) {
            CobolParser.EvaluateStatementContext evalCtx = stmtCtx.evaluateStatement();
            
            // Main EVALUATE expression
            collectFromEvaluateSelect(evalCtx.evaluateSelect(), referencedDataItems);
            
            // ALSO expressions
            for (CobolParser.EvaluateAlsoSelectContext alsoCtx : evalCtx.evaluateAlsoSelect()) {
                collectFromEvaluateSelect(alsoCtx.evaluateSelect(), referencedDataItems);
            }
            
            // WHEN conditions
            for (CobolParser.EvaluateWhenPhraseContext whenCtx : evalCtx.evaluateWhenPhrase()) {
                for (CobolParser.EvaluateWhenContext whenCondCtx : whenCtx.evaluateWhen()) {
                    collectFromEvaluateCondition(whenCondCtx.evaluateCondition(), referencedDataItems);
                    for (CobolParser.EvaluateAlsoConditionContext alsoCondCtx : whenCondCtx.evaluateAlsoCondition()) {
                        collectFromEvaluateCondition(alsoCondCtx.evaluateCondition(), referencedDataItems);
                    }
                }
            }
        }
        
        // EXHIBIT statement
        if (stmtCtx.exhibitStatement() != null) {
            for (CobolParser.ExhibitOperandContext operandCtx : stmtCtx.exhibitStatement().exhibitOperand()) {
                if (operandCtx.identifier() != null) {
                    referencedDataItems.add(operandCtx.identifier().getText());
                }
            }
        }
        
        // EXEC statements - typically don't reference COBOL data items directly
        
        // EXIT statement - no data items
        
        // FREE statement
        if (stmtCtx.freeStatement() != null) {
            if (stmtCtx.freeStatement().identifier() != null) {
                referencedDataItems.add(stmtCtx.freeStatement().identifier().getText());
            }
        }
        
        // GENERATE statement
        if (stmtCtx.generateStatement() != null) {
            if (stmtCtx.generateStatement().reportName() != null) {
                referencedDataItems.add(stmtCtx.generateStatement().reportName().getText());
            }
        }
        
        // GOBACK statement
        if (stmtCtx.gobackStatement() != null) {
            if (stmtCtx.gobackStatement().identifier() != null) {
                referencedDataItems.add(stmtCtx.gobackStatement().identifier().getText());
            }
        }
        
        // GO TO statement - typically references procedure names, not data items
        
        // IF statement
        if (stmtCtx.ifStatement() != null) {
            CobolParser.IfStatementContext ifCtx = stmtCtx.ifStatement();
            
            // Condition
            if (ifCtx.condition() != null) {
                collectFromCondition(ifCtx.condition(), referencedDataItems);
            }
            
            // THEN statements
            if (ifCtx.ifThen() != null) {
                for (CobolParser.StatementContext thenStmtCtx : ifCtx.ifThen().statement()) {
                    collectFromStatement(thenStmtCtx, referencedDataItems);
                }
            }
            
            // ELSE statements
            if (ifCtx.ifElse() != null) {
                for (CobolParser.StatementContext elseStmtCtx : ifCtx.ifElse().statement()) {
                    collectFromStatement(elseStmtCtx, referencedDataItems);
                }
            }
        }
        
        // INITIALIZE statement
        if (stmtCtx.initializeStatement() != null) {
            for (CobolParser.IdentifierContext idCtx : stmtCtx.initializeStatement().identifier()) {
                referencedDataItems.add(idCtx.getText());
            }
            
            // REPLACING phrase
            if (stmtCtx.initializeStatement().initializeReplacingPhrase() != null) {
                for (CobolParser.InitializeReplacingByContext replCtx : 
                    stmtCtx.initializeStatement().initializeReplacingPhrase().initializeReplacingBy()) {
                    if (replCtx.identifier() != null) {
                        referencedDataItems.add(replCtx.identifier().getText());
                    }
                }
            }
        }
        
        // INITIATE statement
        if (stmtCtx.initiateStatement() != null) {
            for (CobolParser.ReportNameContext reportCtx : stmtCtx.initiateStatement().reportName()) {
                referencedDataItems.add(reportCtx.getText());
            }
        }
        
        // INSPECT statement
        if (stmtCtx.inspectStatement() != null) {
            CobolParser.InspectStatementContext inspCtx = stmtCtx.inspectStatement();
            
            // Target identifier
            if (inspCtx.identifier() != null) {
                referencedDataItems.add(inspCtx.identifier().getText());
            }
            
            // TALLYING phrase
            if (inspCtx.inspectTallyingPhrase() != null) {
                for (CobolParser.InspectForContext forCtx : inspCtx.inspectTallyingPhrase().inspectFor()) {
                    if (forCtx.identifier() != null) {
                        referencedDataItems.add(forCtx.identifier().getText());
                    }
                }
            }
            
            // REPLACING phrase
            if (inspCtx.inspectReplacingPhrase() != null) {
                collectFromInspectReplacing(inspCtx.inspectReplacingPhrase(), referencedDataItems);
            }
            
            // TALLYING REPLACING phrase
            if (inspCtx.inspectTallyingReplacingPhrase() != null) {
                for (CobolParser.InspectForContext forCtx : inspCtx.inspectTallyingReplacingPhrase().inspectFor()) {
                    if (forCtx.identifier() != null) {
                        referencedDataItems.add(forCtx.identifier().getText());
                    }
                }
                for (CobolParser.InspectReplacingPhraseContext replCtx : 
                    inspCtx.inspectTallyingReplacingPhrase().inspectReplacingPhrase()) {
                    collectFromInspectReplacing(replCtx, referencedDataItems);
                }
            }
            
            // CONVERTING phrase
            if (inspCtx.inspectConvertingPhrase() != null) {
                if (inspCtx.inspectConvertingPhrase().identifier() != null) {
                    referencedDataItems.add(inspCtx.inspectConvertingPhrase().identifier().getText());
                }
                if (inspCtx.inspectConvertingPhrase().inspectTo() != null &&
                    inspCtx.inspectConvertingPhrase().inspectTo().identifier() != null) {
                    referencedDataItems.add(inspCtx.inspectConvertingPhrase().inspectTo().identifier().getText());
                }
            }
        }
        
        
        if (stmtCtx.invokeStatement() != null) {
            CobolParser.InvokeStatementContext invCtx = stmtCtx.invokeStatement();
            
            // Target object - FIX: Check for multiple identifiers properly
            if (invCtx.identifier() != null && !invCtx.identifier().isEmpty()) {
                // Get the first identifier (target object)
                referencedDataItems.add(invCtx.identifier(0).getText());
            }
            
            // USING parameters
            for (CobolParser.InvokeUsingParameterContext paramCtx : invCtx.invokeUsingParameter()) {
                if (paramCtx.identifier() != null) {
                    referencedDataItems.add(paramCtx.identifier().getText());
                }
            }
            
            // RETURNING parameter - FIX: Get the returning identifier correctly
            if (invCtx.identifier() != null && invCtx.identifier().size() > 1) {
                // Typically the last identifier in INVOKE is the RETURNING variable
                referencedDataItems.add(invCtx.identifier(invCtx.identifier().size() - 1).getText());
            }
        }
        
        
        // JSON GENERATE statement
        if (stmtCtx.jsonGenerateStatement() != null) {
            CobolParser.JsonGenerateStatementContext jsonCtx = stmtCtx.jsonGenerateStatement();
            
            // CORRECT: identifier() returns List<IdentifierContext>
            if (jsonCtx.identifier() != null && !jsonCtx.identifier().isEmpty()) {
                for (CobolParser.IdentifierContext idCtx : jsonCtx.identifier()) {
                    referencedDataItems.add(idCtx.getText());
                }
            }
        }

        // JSON PARSE statement
        if (stmtCtx.jsonParseStatement() != null) {
            CobolParser.JsonParseStatementContext jsonCtx = stmtCtx.jsonParseStatement();
            
            // CORRECT: identifier() returns List<IdentifierContext>
            if (jsonCtx.identifier() != null && !jsonCtx.identifier().isEmpty()) {
                for (CobolParser.IdentifierContext idCtx : jsonCtx.identifier()) {
                    referencedDataItems.add(idCtx.getText());
                }
            }
        }

        // MERGE statement
        if (stmtCtx.mergeStatement() != null) {
            CobolParser.MergeStatementContext mergeCtx = stmtCtx.mergeStatement();
            
            // Sort file
            if (mergeCtx.fileName() != null) {
                referencedDataItems.add(mergeCtx.fileName().getText());
            }
            
            // ON KEY clauses
            for (CobolParser.MergeOnKeyClauseContext keyCtx : mergeCtx.mergeOnKeyClause()) {
                for (CobolParser.QualifiedDataNameContext qualCtx : keyCtx.qualifiedDataName()) {
                    referencedDataItems.add(qualCtx.getText());
                }
            }
            
            // USING files
            for (CobolParser.MergeUsingContext usingCtx : mergeCtx.mergeUsing()) {
                for (CobolParser.FileNameContext fileCtx : usingCtx.fileName()) {
                    referencedDataItems.add(fileCtx.getText());
                }
            }
            
            // GIVING files
            for (CobolParser.MergeGivingPhraseContext givingCtx : mergeCtx.mergeGivingPhrase()) {
                for (CobolParser.MergeGivingContext giveCtx : givingCtx.mergeGiving()) {
                    if (giveCtx.fileName() != null) {
                        referencedDataItems.add(giveCtx.fileName().getText());
                    }
                }
            }
        }
        
        // MOVE statement
        if (stmtCtx.moveStatement() != null) {
            CobolParser.MoveStatementContext moveCtx = stmtCtx.moveStatement();
            
            // MOVE TO format
            if (moveCtx.moveToStatement() != null) {
                CobolParser.MoveToStatementContext moveToCtx = moveCtx.moveToStatement();
                if (moveToCtx.moveToSendingArea() != null && moveToCtx.moveToSendingArea().identifier() != null) {
                    referencedDataItems.add(moveToCtx.moveToSendingArea().identifier().getText());
                }
                for (CobolParser.IdentifierContext destCtx : moveToCtx.identifier()) {
                    referencedDataItems.add(destCtx.getText());
                }
            }
            
            // MOVE CORRESPONDING format
            if (moveCtx.moveCorrespondingToStatement() != null) {
                CobolParser.MoveCorrespondingToStatementContext corrCtx = moveCtx.moveCorrespondingToStatement();
                if (corrCtx.moveCorrespondingToSendingArea() != null && 
                    corrCtx.moveCorrespondingToSendingArea().identifier() != null) {
                    referencedDataItems.add(corrCtx.moveCorrespondingToSendingArea().identifier().getText());
                }
                for (CobolParser.IdentifierContext destCtx : corrCtx.identifier()) {
                    referencedDataItems.add(destCtx.getText());
                }
            }
        }
        
        // MULTIPLY statement
        if (stmtCtx.multiplyStatement() != null) {
            CobolParser.MultiplyStatementContext multCtx = stmtCtx.multiplyStatement();
            
            // Source operand
            if (multCtx.identifier() != null) {
                referencedDataItems.add(multCtx.identifier().getText());
            }
            
            // BY format
            if (multCtx.multiplyRegular() != null) {
                for (CobolParser.MultiplyRegularOperandContext regCtx : multCtx.multiplyRegular().multiplyRegularOperand()) {
                    if (regCtx.identifier() != null) {
                        referencedDataItems.add(regCtx.identifier().getText());
                    }
                }
            }
            
            // GIVING format
            if (multCtx.multiplyGiving() != null) {
                CobolParser.MultiplyGivingContext givingCtx = multCtx.multiplyGiving();
                if (givingCtx.multiplyGivingOperand() != null && givingCtx.multiplyGivingOperand().identifier() != null) {
                    referencedDataItems.add(givingCtx.multiplyGivingOperand().identifier().getText());
                }
                for (CobolParser.MultiplyGivingResultContext resultCtx : givingCtx.multiplyGivingResult()) {
                    if (resultCtx.identifier() != null) {
                        referencedDataItems.add(resultCtx.identifier().getText());
                    }
                }
            }
        }
        
        // NEXT SENTENCE statement - no data items
        
        // OPEN statement
        if (stmtCtx.openStatement() != null) {
            CobolParser.OpenStatementContext openCtx = stmtCtx.openStatement();
            
            // INPUT files
            for (CobolParser.OpenInputStatementContext inputCtx : openCtx.openInputStatement()) {
                for (CobolParser.OpenInputContext inCtx : inputCtx.openInput()) {
                    if (inCtx.fileName() != null) {
                        referencedDataItems.add(inCtx.fileName().getText());
                    }
                }
            }
            
            // OUTPUT files
            for (CobolParser.OpenOutputStatementContext outputCtx : openCtx.openOutputStatement()) {
                for (CobolParser.OpenOutputContext outCtx : outputCtx.openOutput()) {
                    if (outCtx.fileName() != null) {
                        referencedDataItems.add(outCtx.fileName().getText());
                    }
                }
            }
            
            // I-O files
            for (CobolParser.OpenIOStatementContext ioCtx : openCtx.openIOStatement()) {
                for (CobolParser.FileNameContext fileCtx : ioCtx.fileName()) {
                    referencedDataItems.add(fileCtx.getText());
                }
            }
            
            // EXTEND files
            for (CobolParser.OpenExtendStatementContext extendCtx : openCtx.openExtendStatement()) {
                for (CobolParser.FileNameContext fileCtx : extendCtx.fileName()) {
                    referencedDataItems.add(fileCtx.getText());
                }
            }
        }
        
        // PERFORM statement
        if (stmtCtx.performStatement() != null) {
            CobolParser.PerformStatementContext perfCtx = stmtCtx.performStatement();
            
            // Inline PERFORM
            if (perfCtx.performInlineStatement() != null) {
                CobolParser.PerformInlineStatementContext inlineCtx = perfCtx.performInlineStatement();
                
                // Perform type variables
                if (inlineCtx.performType() != null) {
                    collectFromPerformType(inlineCtx.performType(), referencedDataItems);
                }
                
                // Inline statements
                for (CobolParser.StatementContext stmtInlineCtx : inlineCtx.statement()) {
                    Util.collectFromStatement(stmtInlineCtx, referencedDataItems);
                }
            }
            
            // Procedure PERFORM
            if (perfCtx.performProcedureStatement() != null) {
                CobolParser.PerformProcedureStatementContext procCtx = perfCtx.performProcedureStatement();
                
                // Perform type variables
                if (procCtx.performType() != null) {
                    collectFromPerformType(procCtx.performType(), referencedDataItems);
                }
            }
        }
        
        // PURGE statement
        if (stmtCtx.purgeStatement() != null) {
            for (CobolParser.CdNameContext cdCtx : stmtCtx.purgeStatement().cdName()) {
                referencedDataItems.add(cdCtx.getText());
            }
        }
        
        // RAISE statement
        if (stmtCtx.raiseStatement() != null) {
            if (stmtCtx.raiseStatement().identifier() != null) {
                referencedDataItems.add(stmtCtx.raiseStatement().identifier().getText());
            }
        }
        
        // READ statement
        if (stmtCtx.readStatement() != null) {
            CobolParser.ReadStatementContext readCtx = stmtCtx.readStatement();
            
            // File name
            if (readCtx.fileName() != null) {
                referencedDataItems.add(readCtx.fileName().getText());
            }
            
            // INTO clause
            if (readCtx.readInto() != null && readCtx.readInto().identifier() != null) {
                referencedDataItems.add(readCtx.readInto().identifier().getText());
            }
            
            // KEY clause
            if (readCtx.readKey() != null && readCtx.readKey().qualifiedDataName() != null) {
                referencedDataItems.add(readCtx.readKey().qualifiedDataName().getText());
            }
        }
        
        // RECEIVE statement
        if (stmtCtx.receiveStatement() != null) {
            CobolParser.ReceiveStatementContext recCtx = stmtCtx.receiveStatement();
            
            // FROM format
            if (recCtx.receiveFromStatement() != null) {
                CobolParser.ReceiveFromStatementContext fromCtx = recCtx.receiveFromStatement();
                if (fromCtx.dataName() != null) {
                    referencedDataItems.add(fromCtx.dataName().getText());
                }
                
                // Thread data items
                for (CobolParser.ReceiveThreadContext threadCtx : fromCtx.receiveThread()) {
                    if (threadCtx.dataName() != null) {
                        referencedDataItems.add(threadCtx.dataName().getText());
                    }
                }
                
                // Size data items
                for (CobolParser.ReceiveSizeContext sizeCtx : fromCtx.receiveSize()) {
                    if (sizeCtx.identifier() != null) {
                        referencedDataItems.add(sizeCtx.identifier().getText());
                    }
                }
                
                // Status data items
                for (CobolParser.ReceiveStatusContext statusCtx : fromCtx.receiveStatus()) {
                    if (statusCtx.identifier() != null) {
                        referencedDataItems.add(statusCtx.identifier().getText());
                    }
                }
            }
            
            // INTO format
            if (recCtx.receiveIntoStatement() != null) {
                CobolParser.ReceiveIntoStatementContext intoCtx = recCtx.receiveIntoStatement();
                if (intoCtx.cdName() != null) {
                    referencedDataItems.add(intoCtx.cdName().getText());
                }
                if (intoCtx.identifier() != null) {
                    referencedDataItems.add(intoCtx.identifier().getText());
                }
            }
        }
        
        // RELEASE statement
        if (stmtCtx.releaseStatement() != null) {
            CobolParser.ReleaseStatementContext relCtx = stmtCtx.releaseStatement();
            if (relCtx.recordName() != null) {
                referencedDataItems.add(relCtx.recordName().getText());
            }
            if (relCtx.qualifiedDataName() != null) {
                referencedDataItems.add(relCtx.qualifiedDataName().getText());
            }
        }
        
        // RESUME statement - typically no data items
        
        // RETURN statement
        if (stmtCtx.returnStatement() != null) {
            CobolParser.ReturnStatementContext retCtx = stmtCtx.returnStatement();
            if (retCtx.fileName() != null) {
                referencedDataItems.add(retCtx.fileName().getText());
            }
            if (retCtx.returnInto() != null && retCtx.returnInto().qualifiedDataName() != null) {
                referencedDataItems.add(retCtx.returnInto().qualifiedDataName().getText());
            }
        }
        
        // REWRITE statement
        if (stmtCtx.rewriteStatement() != null) {
            CobolParser.RewriteStatementContext rewCtx = stmtCtx.rewriteStatement();
            if (rewCtx.recordName() != null) {
                referencedDataItems.add(rewCtx.recordName().getText());
            }
            if (rewCtx.rewriteFrom() != null && rewCtx.rewriteFrom().identifier() != null) {
                referencedDataItems.add(rewCtx.rewriteFrom().identifier().getText());
            }
        }
        
        // SEARCH statement
        if (stmtCtx.searchStatement() != null) {
            CobolParser.SearchStatementContext searchCtx = stmtCtx.searchStatement();
            
            // Search target
            if (searchCtx.qualifiedDataName() != null) {
                referencedDataItems.add(searchCtx.qualifiedDataName().getText());
            }
            
            // VARYING clause
            if (searchCtx.searchVarying() != null && searchCtx.searchVarying().qualifiedDataName() != null) {
                referencedDataItems.add(searchCtx.searchVarying().qualifiedDataName().getText());
            }
            
            // WHEN conditions
            for (CobolParser.SearchWhenContext whenCtx : searchCtx.searchWhen()) {
                if (whenCtx.condition() != null) {
                    collectFromCondition(whenCtx.condition(), referencedDataItems);
                }
                
                // WHEN statements
                for (CobolParser.StatementContext whenStmtCtx : whenCtx.statement()) {
                    collectFromStatement(whenStmtCtx, referencedDataItems);
                }
            }
        }
        
        // SEND statement
        if (stmtCtx.sendStatement() != null) {
            CobolParser.SendStatementContext sendCtx = stmtCtx.sendStatement();
            
            // SYNC format
            if (sendCtx.sendStatementSync() != null) {
                CobolParser.SendStatementSyncContext syncCtx = sendCtx.sendStatementSync();
                if (syncCtx.cdName() != null) {
                    referencedDataItems.add(syncCtx.cdName().getText());
                }
            }
            
            // ASYNC format
            if (sendCtx.sendStatementAsync() != null) {
                CobolParser.SendStatementAsyncContext asyncCtx = sendCtx.sendStatementAsync();
                if (asyncCtx.identifier() != null) {
                    referencedDataItems.add(asyncCtx.identifier().getText());
                }
            }
            
            // COMM format
            if (sendCtx.sendStatementComm() != null) {
                CobolParser.SendStatementCommContext commCtx = sendCtx.sendStatementComm();
                if (commCtx.cdName() != null) {
                    referencedDataItems.add(commCtx.cdName().getText());
                }
                if (commCtx.sendFromPhrase() != null && commCtx.sendFromPhrase().identifier() != null) {
                    referencedDataItems.add(commCtx.sendFromPhrase().identifier().getText());
                }
            }
        }
        
        // SET statement
        if (stmtCtx.setStatement() != null) {
            CobolParser.SetStatementContext setCtx = stmtCtx.setStatement();
            
            // SET TO format
            for (CobolParser.SetToStatementContext setToCtx : setCtx.setToStatement()) {
                for (CobolParser.SetToContext toCtx : setToCtx.setTo()) {
                    if (toCtx.identifier() != null) {
                        referencedDataItems.add(toCtx.identifier().getText());
                    }
                }
                for (CobolParser.SetToValueContext valueCtx : setToCtx.setToValue()) {
                    if (valueCtx.identifier() != null) {
                        referencedDataItems.add(valueCtx.identifier().getText());
                    }
                }
            }
            
            // SET UP/DOWN BY format
            if (setCtx.setUpDownByStatement() != null) {
                for (CobolParser.SetToContext toCtx : setCtx.setUpDownByStatement().setTo()) {
                    if (toCtx.identifier() != null) {
                        referencedDataItems.add(toCtx.identifier().getText());
                    }
                }
                if (setCtx.setUpDownByStatement().setByValue() != null &&
                    setCtx.setUpDownByStatement().setByValue().identifier() != null) {
                    referencedDataItems.add(setCtx.setUpDownByStatement().setByValue().identifier().getText());
                }
            }
            
            // SET condition format
            if (setCtx.setConditionStatement() != null) {
                for (CobolParser.ConditionNameContext condCtx : setCtx.setConditionStatement().conditionName()) {
                    referencedDataItems.add(condCtx.getText());
                }
            }
        }
        
        // SORT statement
        if (stmtCtx.sortStatement() != null) {
            CobolParser.SortStatementContext sortCtx = stmtCtx.sortStatement();
            
            // Sort file
            if (sortCtx.fileName() != null) {
                referencedDataItems.add(sortCtx.fileName().getText());
            }
            
            // ON KEY clauses
            for (CobolParser.SortOnKeyClauseContext keyCtx : sortCtx.sortOnKeyClause()) {
                for (CobolParser.QualifiedDataNameContext qualCtx : keyCtx.qualifiedDataName()) {
                    referencedDataItems.add(qualCtx.getText());
                }
            }
            
            // USING files
            for (CobolParser.SortUsingContext usingCtx : sortCtx.sortUsing()) {
                for (CobolParser.FileNameContext fileCtx : usingCtx.fileName()) {
                    referencedDataItems.add(fileCtx.getText());
                }
            }
            
            // GIVING files
            for (CobolParser.SortGivingPhraseContext givingCtx : sortCtx.sortGivingPhrase()) {
                for (CobolParser.SortGivingContext giveCtx : givingCtx.sortGiving()) {
                    if (giveCtx.fileName() != null) {
                        referencedDataItems.add(giveCtx.fileName().getText());
                    }
                }
            }
        }
        
        // START statement
        if (stmtCtx.startStatement() != null) {
            CobolParser.StartStatementContext startCtx = stmtCtx.startStatement();
            if (startCtx.fileName() != null) {
                referencedDataItems.add(startCtx.fileName().getText());
            }
            if (startCtx.startKey() != null && startCtx.startKey().qualifiedDataName() != null) {
                referencedDataItems.add(startCtx.startKey().qualifiedDataName().getText());
            }
        }
        
        // STOP statement
        if (stmtCtx.stopStatement() != null) {
            CobolParser.StopStatementContext stopCtx = stmtCtx.stopStatement();
            if (stopCtx.stopStatementGiving() != null) {
                if (stopCtx.stopStatementGiving().identifier() != null) {
                    referencedDataItems.add(stopCtx.stopStatementGiving().identifier().getText());
                }
            }
        }
        
        // STRING statement
        if (stmtCtx.stringStatement() != null) {
            CobolParser.StringStatementContext strCtx = stmtCtx.stringStatement();
            
            // Sending phrases
            for (CobolParser.StringSendingPhraseContext sendingCtx : strCtx.stringSendingPhrase()) {
                for (CobolParser.StringSendingContext sendCtx : sendingCtx.stringSending()) {
                    if (sendCtx.identifier() != null) {
                        referencedDataItems.add(sendCtx.identifier().getText());
                    }
                }
                
                // DELIMITED BY
                if (sendingCtx.stringDelimitedByPhrase() != null) {
                    if (sendingCtx.stringDelimitedByPhrase().identifier() != null) {
                        referencedDataItems.add(sendingCtx.stringDelimitedByPhrase().identifier().getText());
                    }
                }
                
                // FOR
                if (sendingCtx.stringForPhrase() != null) {
                    if (sendingCtx.stringForPhrase().identifier() != null) {
                        referencedDataItems.add(sendingCtx.stringForPhrase().identifier().getText());
                    }
                }
            }
            
            // INTO phrase
            if (strCtx.stringIntoPhrase() != null && strCtx.stringIntoPhrase().identifier() != null) {
                referencedDataItems.add(strCtx.stringIntoPhrase().identifier().getText());
            }
            
            // WITH POINTER phrase
            if (strCtx.stringWithPointerPhrase() != null && 
                strCtx.stringWithPointerPhrase().qualifiedDataName() != null) {
                referencedDataItems.add(strCtx.stringWithPointerPhrase().qualifiedDataName().getText());
            }
        }
        
        // SUBTRACT statement
        if (stmtCtx.subtractStatement() != null) {
            CobolParser.SubtractStatementContext subCtx = stmtCtx.subtractStatement();
            
            // FROM format
            if (subCtx.subtractFromStatement() != null) {
                CobolParser.SubtractFromStatementContext fromCtx = subCtx.subtractFromStatement();
                for (CobolParser.SubtractSubtrahendContext subtrahendCtx : fromCtx.subtractSubtrahend()) {
                    if (subtrahendCtx.identifier() != null) {
                        referencedDataItems.add(subtrahendCtx.identifier().getText());
                    }
                }
                for (CobolParser.SubtractMinuendContext minuendCtx : fromCtx.subtractMinuend()) {
                    if (minuendCtx.identifier() != null) {
                        referencedDataItems.add(minuendCtx.identifier().getText());
                    }
                }
            }
            
            // FROM GIVING format
            if (subCtx.subtractFromGivingStatement() != null) {
                CobolParser.SubtractFromGivingStatementContext givingCtx = subCtx.subtractFromGivingStatement();
                for (CobolParser.SubtractSubtrahendContext subtrahendCtx : givingCtx.subtractSubtrahend()) {
                    if (subtrahendCtx.identifier() != null) {
                        referencedDataItems.add(subtrahendCtx.identifier().getText());
                    }
                }
                if (givingCtx.subtractMinuendGiving() != null && 
                    givingCtx.subtractMinuendGiving().identifier() != null) {
                    referencedDataItems.add(givingCtx.subtractMinuendGiving().identifier().getText());
                }
                for (CobolParser.SubtractGivingContext giveCtx : givingCtx.subtractGiving()) {
                    if (giveCtx.identifier() != null) {
                        referencedDataItems.add(giveCtx.identifier().getText());
                    }
                }
            }
            
            // CORRESPONDING format
            if (subCtx.subtractCorrespondingStatement() != null) {
                CobolParser.SubtractCorrespondingStatementContext corrCtx = subCtx.subtractCorrespondingStatement();
                if (corrCtx.qualifiedDataName() != null) {
                    referencedDataItems.add(corrCtx.qualifiedDataName().getText());
                }
                if (corrCtx.subtractMinuendCorresponding() != null &&
                    corrCtx.subtractMinuendCorresponding().qualifiedDataName() != null) {
                    referencedDataItems.add(corrCtx.subtractMinuendCorresponding().qualifiedDataName().getText());
                }
            }
        }
        
        // TERMINATE statement
        if (stmtCtx.terminateStatement() != null) {
            if (stmtCtx.terminateStatement().reportName() != null) {
                referencedDataItems.add(stmtCtx.terminateStatement().reportName().getText());
            }
        }
        
        // UNSTRING statement
        if (stmtCtx.unstringStatement() != null) {
            CobolParser.UnstringStatementContext unstrCtx = stmtCtx.unstringStatement();
            
            // Sending phrase
            if (unstrCtx.unstringSendingPhrase() != null && 
                unstrCtx.unstringSendingPhrase().identifier() != null) {
                referencedDataItems.add(unstrCtx.unstringSendingPhrase().identifier().getText());
            }
            
            // DELIMITED BY
            if (unstrCtx.unstringSendingPhrase() != null && 
                unstrCtx.unstringSendingPhrase().unstringDelimitedByPhrase() != null) {
                if (unstrCtx.unstringSendingPhrase().unstringDelimitedByPhrase().identifier() != null) {
                    referencedDataItems.add(unstrCtx.unstringSendingPhrase().unstringDelimitedByPhrase().identifier().getText());
                }
            }
            
            // INTO phrase
            if (unstrCtx.unstringIntoPhrase() != null) {
                for (CobolParser.UnstringIntoContext intoCtx : unstrCtx.unstringIntoPhrase().unstringInto()) {
                    if (intoCtx.identifier() != null) {
                        referencedDataItems.add(intoCtx.identifier().getText());
                    }
                    if (intoCtx.unstringDelimiterIn() != null && 
                        intoCtx.unstringDelimiterIn().identifier() != null) {
                        referencedDataItems.add(intoCtx.unstringDelimiterIn().identifier().getText());
                    }
                    if (intoCtx.unstringCountIn() != null && 
                        intoCtx.unstringCountIn().identifier() != null) {
                        referencedDataItems.add(intoCtx.unstringCountIn().identifier().getText());
                    }
                }
            }
            
            // WITH POINTER phrase
            if (unstrCtx.unstringWithPointerPhrase() != null && 
                unstrCtx.unstringWithPointerPhrase().qualifiedDataName() != null) {
                referencedDataItems.add(unstrCtx.unstringWithPointerPhrase().qualifiedDataName().getText());
            }
            
            // TALLYING phrase
            if (unstrCtx.unstringTallyingPhrase() != null && 
                unstrCtx.unstringTallyingPhrase().qualifiedDataName() != null) {
                referencedDataItems.add(unstrCtx.unstringTallyingPhrase().qualifiedDataName().getText());
            }
        }
        
        // WRITE statement
        if (stmtCtx.writeStatement() != null) {
            CobolParser.WriteStatementContext writeCtx = stmtCtx.writeStatement();
            
            // Record name
            if (writeCtx.recordName() != null) {
                referencedDataItems.add(writeCtx.recordName().getText());
            }
            
            // FROM phrase
            if (writeCtx.writeFromPhrase() != null && writeCtx.writeFromPhrase().identifier() != null) {
                referencedDataItems.add(writeCtx.writeFromPhrase().identifier().getText());
            }
            
            // ADVANCING phrase
            if (writeCtx.writeAdvancingPhrase() != null) {
                if (writeCtx.writeAdvancingPhrase().writeAdvancingLines() != null) {
                    if (writeCtx.writeAdvancingPhrase().writeAdvancingLines().identifier() != null) {
                        referencedDataItems.add(writeCtx.writeAdvancingPhrase().writeAdvancingLines().identifier().getText());
                    }
                }
            }
        }
        
        // XML GENERATE statement

        // trying both approach, first as a list, then as a scalar
        // Fix: XML GENERATE statement- Actually returns List<IdentifierContext>
        // Fix: XML GENERATE statement - CORRECTED SYNTAX
        if (stmtCtx.xmlGenerateStatement() != null) {
            CobolParser.XmlGenerateStatementContext xmlCtx = stmtCtx.xmlGenerateStatement();
            
            // CORRECT: identifier() returns List<IdentifierContext>
            if (xmlCtx.identifier() != null && !xmlCtx.identifier().isEmpty()) {
                for (CobolParser.IdentifierContext idCtx : xmlCtx.identifier()) {
                    referencedDataItems.add(idCtx.getText());
                }
            }
        }

        // Fix: XML PARSE statement - CORRECTED SYNTAX
        // YK: TO DO:

        // EXEC statement - handle SQL and CICS
        if (stmtCtx.execStatement() != null) {
            // EXEC SQL and EXEC CICS typically don't reference COBOL data items directly
            // but could be enhanced to parse host variables if needed
        }
        
        // UNKNOWN statement - try to extract any identifiers
        if (stmtCtx.unknownStatement() != null) {
            // Basic extraction for unknown statements - this is a fallback
            String text = stmtCtx.unknownStatement().getText();
            // This would need more sophisticated parsing for real use
        }
    }

    // Helper methods for complex statement analysis

    private static void collectFromArithmeticExpression(CobolParser.ArithmeticExpressionContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            // Collect from multDivs
            if (ctx.multDivs() != null) {
                collectFromMultDivs(ctx.multDivs(), referencedDataItems);
            }
            
            // Collect from plusMinus
            for (CobolParser.PlusMinusContext pmCtx : ctx.plusMinus()) {
                if (pmCtx.multDivs() != null) {
                    collectFromMultDivs(pmCtx.multDivs(), referencedDataItems);
                }
            }
        }
    }

    private static void collectFromMultDivs(CobolParser.MultDivsContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            // Collect from powers
            if (ctx.powers() != null) {
                collectFromPowers(ctx.powers(), referencedDataItems);
            }
            
            // Collect from multDiv
            for (CobolParser.MultDivContext mdCtx : ctx.multDiv()) {
                if (mdCtx.powers() != null) {
                    collectFromPowers(mdCtx.powers(), referencedDataItems);
                }
            }
        }
    }

    private static void collectFromPowers(CobolParser.PowersContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            // Collect from basis
            if (ctx.basis() != null) {
                collectFromBasis(ctx.basis(), referencedDataItems);
            }
            
            // Collect from power
            for (CobolParser.PowerContext pCtx : ctx.power()) {
                if (pCtx.basis() != null) {
                    collectFromBasis(pCtx.basis(), referencedDataItems);
                }
            }
        }
    }

    private static void collectFromBasis(CobolParser.BasisContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            if (ctx.identifier() != null) {
                referencedDataItems.add(ctx.identifier().getText());
            } else if (ctx.arithmeticExpression() != null) {
                collectFromArithmeticExpression(ctx.arithmeticExpression(), referencedDataItems);
            }
        }
    }

    private static void collectFromCondition(CobolParser.ConditionContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            // Collect from combinable condition
            if (ctx.combinableCondition() != null) {
                collectFromCombinableCondition(ctx.combinableCondition(), referencedDataItems);
            }
            
            // Collect from AND/OR conditions
            for (CobolParser.AndOrConditionContext aoCtx : ctx.andOrCondition()) {
                if (aoCtx.combinableCondition() != null) {
                    collectFromCombinableCondition(aoCtx.combinableCondition(), referencedDataItems);
                }
                for (CobolParser.AbbreviationContext abbCtx : aoCtx.abbreviation()) {
                    collectFromAbbreviation(abbCtx, referencedDataItems);
                }
            }
        }
    }

    private static void collectFromCombinableCondition(CobolParser.CombinableConditionContext ctx, Set<String> referencedDataItems) {
        if (ctx != null && ctx.simpleCondition() != null) {
            collectFromSimpleCondition(ctx.simpleCondition(), referencedDataItems);
        }
    }

    private static void collectFromSimpleCondition(CobolParser.SimpleConditionContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            if (ctx.condition() != null) {
                collectFromCondition(ctx.condition(), referencedDataItems);
            } else if (ctx.relationCondition() != null) {
                collectFromRelationCondition(ctx.relationCondition(), referencedDataItems);
            } else if (ctx.classCondition() != null) {
                if (ctx.classCondition().identifier() != null) {
                    referencedDataItems.add(ctx.classCondition().identifier().getText());
                }
            } else if (ctx.conditionNameReference() != null) {
                if (ctx.conditionNameReference().conditionName() != null) {
                    referencedDataItems.add(ctx.conditionNameReference().conditionName().getText());
                }
            }
        }
    }

    private static void collectFromRelationCondition(CobolParser.RelationConditionContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            if (ctx.relationSignCondition() != null && ctx.relationSignCondition().arithmeticExpression() != null) {
                collectFromArithmeticExpression(ctx.relationSignCondition().arithmeticExpression(), referencedDataItems);
            } else if (ctx.relationArithmeticComparison() != null) {
                for (CobolParser.ArithmeticExpressionContext arithCtx : ctx.relationArithmeticComparison().arithmeticExpression()) {
                    collectFromArithmeticExpression(arithCtx, referencedDataItems);
                }
            } else if (ctx.relationCombinedComparison() != null) {
                if (ctx.relationCombinedComparison().arithmeticExpression() != null) {
                    collectFromArithmeticExpression(ctx.relationCombinedComparison().arithmeticExpression(), referencedDataItems);
                }
                if (ctx.relationCombinedComparison().relationCombinedCondition() != null) {
                    for (CobolParser.ArithmeticExpressionContext arithCtx : 
                        ctx.relationCombinedComparison().relationCombinedCondition().arithmeticExpression()) {
                        collectFromArithmeticExpression(arithCtx, referencedDataItems);
                    }
                }
            }
        }
    }

    private static void collectFromAbbreviation(CobolParser.AbbreviationContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            if (ctx.arithmeticExpression() != null) {
                collectFromArithmeticExpression(ctx.arithmeticExpression(), referencedDataItems);
            }
            if (ctx.abbreviation() != null) {
                collectFromAbbreviation(ctx.abbreviation(), referencedDataItems);
            }
        }
    }

    private static void collectFromEvaluateSelect(CobolParser.EvaluateSelectContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            if (ctx.identifier() != null) {
                referencedDataItems.add(ctx.identifier().getText());
            } else if (ctx.arithmeticExpression() != null) {
                collectFromArithmeticExpression(ctx.arithmeticExpression(), referencedDataItems);
            } else if (ctx.condition() != null) {
                collectFromCondition(ctx.condition(), referencedDataItems);
            }
        }
    }

    private static void collectFromEvaluateCondition(CobolParser.EvaluateConditionContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            if (ctx.evaluateValue() != null) {
                collectFromEvaluateValue(ctx.evaluateValue(), referencedDataItems);
            }
            if (ctx.evaluateThrough() != null && ctx.evaluateThrough().evaluateValue() != null) {
                collectFromEvaluateValue(ctx.evaluateThrough().evaluateValue(), referencedDataItems);
            }
            if (ctx.condition() != null) {
                collectFromCondition(ctx.condition(), referencedDataItems);
            }
        }
    }

    private static void collectFromEvaluateValue(CobolParser.EvaluateValueContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            if (ctx.identifier() != null) {
                referencedDataItems.add(ctx.identifier().getText());
            } else if (ctx.arithmeticExpression() != null) {
                collectFromArithmeticExpression(ctx.arithmeticExpression(), referencedDataItems);
            }
        }
    }

    private static void collectFromInspectReplacing(CobolParser.InspectReplacingPhraseContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            for (CobolParser.InspectReplacingCharactersContext charCtx : ctx.inspectReplacingCharacters()) {
                if (charCtx.inspectBy() != null && charCtx.inspectBy().identifier() != null) {
                    referencedDataItems.add(charCtx.inspectBy().identifier().getText());
                }
            }
            for (CobolParser.InspectReplacingAllLeadingsContext allCtx : ctx.inspectReplacingAllLeadings()) {
                for (CobolParser.InspectReplacingAllLeadingContext replCtx : allCtx.inspectReplacingAllLeading()) {
                    if (replCtx.identifier() != null) {
                        referencedDataItems.add(replCtx.identifier().getText());
                    }
                    if (replCtx.inspectBy() != null && replCtx.inspectBy().identifier() != null) {
                        referencedDataItems.add(replCtx.inspectBy().identifier().getText());
                    }
                }
            }
        }
    }

    private static void collectFromPerformType(CobolParser.PerformTypeContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            if (ctx.performTimes() != null && ctx.performTimes().identifier() != null) {
                referencedDataItems.add(ctx.performTimes().identifier().getText());
            } else if (ctx.performUntil() != null && ctx.performUntil().condition() != null) {
                collectFromCondition(ctx.performUntil().condition(), referencedDataItems);
            } else if (ctx.performVarying() != null) {
                collectFromPerformVarying(ctx.performVarying(), referencedDataItems);
            }
        }
    }

    private static void collectFromPerformVarying(CobolParser.PerformVaryingContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            if (ctx.performVaryingClause() != null) {
                collectFromPerformVaryingClause(ctx.performVaryingClause(), referencedDataItems);
            }
        }
    }

    private static void collectFromPerformVaryingClause(CobolParser.PerformVaryingClauseContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            if (ctx.performVaryingPhrase() != null) {
                collectFromPerformVaryingPhrase(ctx.performVaryingPhrase(), referencedDataItems);
            }
            
            // AFTER clauses
            for (CobolParser.PerformAfterContext afterCtx : ctx.performAfter()) {
                if (afterCtx.performVaryingPhrase() != null) {
                    collectFromPerformVaryingPhrase(afterCtx.performVaryingPhrase(), referencedDataItems);
                }
            }
        }
    }

    private static void collectFromPerformVaryingPhrase(CobolParser.PerformVaryingPhraseContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            // VARYING variable
            if (ctx.identifier() != null) {
                referencedDataItems.add(ctx.identifier().getText());
            }
            
            // FROM clause
            if (ctx.performFrom() != null) {
                collectFromPerformFrom(ctx.performFrom(), referencedDataItems);
            }
            
            // BY clause
            if (ctx.performBy() != null) {
                collectFromPerformBy(ctx.performBy(), referencedDataItems);
            }
            
            // UNTIL clause
            if (ctx.performUntil() != null && ctx.performUntil().condition() != null) {
                collectFromCondition(ctx.performUntil().condition(), referencedDataItems);
            }
        }
    }

    private static void collectFromPerformFrom(CobolParser.PerformFromContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            if (ctx.identifier() != null) {
                referencedDataItems.add(ctx.identifier().getText());
            } else if (ctx.arithmeticExpression() != null) {
                collectFromArithmeticExpression(ctx.arithmeticExpression(), referencedDataItems);
            }
        }
    }

    private static void collectFromPerformBy(CobolParser.PerformByContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            if (ctx.identifier() != null) {
                referencedDataItems.add(ctx.identifier().getText());
            } else if (ctx.arithmeticExpression() != null) {
                collectFromArithmeticExpression(ctx.arithmeticExpression(), referencedDataItems);
            }
        }
    }

    /**
     * Utility method to extract all qualified data names from a context
     * This is a helper for contexts that might contain qualified data names
     */
    private static void collectFromQualifiedDataName(CobolParser.QualifiedDataNameContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            // Extract the main data name
            String fullName = ctx.getText();
            referencedDataItems.add(fullName);
            
            // Also extract individual components if needed
            if (ctx.qualifiedDataNameFormat1() != null) {
                CobolParser.QualifiedDataNameFormat1Context format1 = ctx.qualifiedDataNameFormat1();
                if (format1.dataName() != null) {
                    referencedDataItems.add(format1.dataName().getText());
                }
                if (format1.conditionName() != null) {
                    referencedDataItems.add(format1.conditionName().getText());
                }
            } else if (ctx.qualifiedDataNameFormat2() != null) {
                CobolParser.QualifiedDataNameFormat2Context format2 = ctx.qualifiedDataNameFormat2();
                if (format2.paragraphName() != null) {
                    referencedDataItems.add(format2.paragraphName().getText());
                }
            } else if (ctx.qualifiedDataNameFormat3() != null) {
                CobolParser.QualifiedDataNameFormat3Context format3 = ctx.qualifiedDataNameFormat3();
                if (format3.textName() != null) {
                    referencedDataItems.add(format3.textName().getText());
                }
            }
        }
    }

    /**
     * Utility method to extract identifiers from generic identifier contexts
     * This handles table calls, function calls, and other complex identifier forms
     */
    private static void collectFromIdentifier(CobolParser.IdentifierContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            if (ctx.qualifiedDataName() != null) {
                collectFromQualifiedDataName(ctx.qualifiedDataName(), referencedDataItems);
            } else if (ctx.tableCall() != null) {
                collectFromTableCall(ctx.tableCall(), referencedDataItems);
            } else if (ctx.functionCall() != null) {
                collectFromFunctionCall(ctx.functionCall(), referencedDataItems);
            } else if (ctx.specialRegister() != null) {
                collectFromSpecialRegister(ctx.specialRegister(), referencedDataItems);
            } else if (ctx.objectReference() != null) {
                collectFromObjectReference(ctx.objectReference(), referencedDataItems);
            } else if (ctx.methodReference() != null) {
                collectFromMethodReference(ctx.methodReference(), referencedDataItems);
            }
        }
    }

    private static void collectFromTableCall(CobolParser.TableCallContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            // Main table name
            if (ctx.qualifiedDataName() != null) {
                collectFromQualifiedDataName(ctx.qualifiedDataName(), referencedDataItems);
            }
            
            // Subscripts
            for (CobolParser.SubscriptContext subCtx : ctx.subscript()) {
                collectFromSubscript(subCtx, referencedDataItems);
            }
            
            // Reference modifier
            if (ctx.referenceModifier() != null) {
                collectFromReferenceModifier(ctx.referenceModifier(), referencedDataItems);
            }
        }
    }

    private static void collectFromFunctionCall(CobolParser.FunctionCallContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            // Function arguments
            for (CobolParser.ArgumentContext argCtx : ctx.argument()) {
                collectFromArgument(argCtx, referencedDataItems);
            }
            
            // Reference modifier
            if (ctx.referenceModifier() != null) {
                collectFromReferenceModifier(ctx.referenceModifier(), referencedDataItems);
            }
        }
    }

    private static void collectFromSpecialRegister(CobolParser.SpecialRegisterContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            String text = ctx.getText().toUpperCase();
            
            // CORRECT: Single identifier
            if ((text.contains("LENGTH") || text.contains("ADDRESS")) && text.contains("OF")) {
                if (ctx.identifier() != null) {
                    referencedDataItems.add(ctx.identifier().getText());
                }
            }
            
            referencedDataItems.add(ctx.getText());
        }
    }

    private static void collectFromObjectReference(CobolParser.ObjectReferenceContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            for (CobolParser.QualifiedDataNameContext qualCtx : ctx.qualifiedDataName()) {
                collectFromQualifiedDataName(qualCtx, referencedDataItems);
            }
        }
    }

    private  static void collectFromMethodReference(CobolParser.MethodReferenceContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            if (ctx.qualifiedDataName() != null) {
                collectFromQualifiedDataName(ctx.qualifiedDataName(), referencedDataItems);
            }
        }
    }

    private static void collectFromSubscript(CobolParser.SubscriptContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            if (ctx.qualifiedDataName() != null) {
                collectFromQualifiedDataName(ctx.qualifiedDataName(), referencedDataItems);
            } else if (ctx.indexName() != null) {
                referencedDataItems.add(ctx.indexName().getText());
            } else if (ctx.arithmeticExpression() != null) {
                collectFromArithmeticExpression(ctx.arithmeticExpression(), referencedDataItems);
            }
        }
    }

    private static void collectFromArgument(CobolParser.ArgumentContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            if (ctx.identifier() != null) {
                collectFromIdentifier(ctx.identifier(), referencedDataItems);
            } else if (ctx.qualifiedDataName() != null) {
                collectFromQualifiedDataName(ctx.qualifiedDataName(), referencedDataItems);
            } else if (ctx.indexName() != null) {
                referencedDataItems.add(ctx.indexName().getText());
            } else if (ctx.arithmeticExpression() != null) {
                collectFromArithmeticExpression(ctx.arithmeticExpression(), referencedDataItems);
            }
        }
    }

    private static void collectFromReferenceModifier(CobolParser.ReferenceModifierContext ctx, Set<String> referencedDataItems) {
        if (ctx != null) {
            if (ctx.characterPosition() != null && ctx.characterPosition().arithmeticExpression() != null) {
                collectFromArithmeticExpression(ctx.characterPosition().arithmeticExpression(), referencedDataItems);
            }
            if (ctx.length() != null && ctx.length().arithmeticExpression() != null) {
                collectFromArithmeticExpression(ctx.length().arithmeticExpression(), referencedDataItems);
            }
        }
    }

    /**
     * Enhanced method to collect data items from exception handling clauses
     * Many statements have exception handling that can reference data items
     */
    private static void collectFromExceptionClauses(CobolParser.StatementContext stmtCtx, Set<String> referencedDataItems) {
        // This is a generic method to handle common exception clauses
        // Individual statement handlers above should call this for completeness
        
        String stmtText = stmtCtx.getText().toUpperCase();
        
        // Look for common exception patterns and extract data items
        // This is a simplified approach - for production use, you'd want to parse the actual exception clauses
        
        if (stmtText.contains("ON EXCEPTION") || stmtText.contains("NOT ON EXCEPTION")) {
            // Extract identifiers from exception handling code
            // This would require more sophisticated parsing
        }
        
        if (stmtText.contains("ON SIZE ERROR") || stmtText.contains("NOT ON SIZE ERROR")) {
            // Extract identifiers from size error handling code
        }
        
        if (stmtText.contains("AT END") || stmtText.contains("NOT AT END")) {
            // Extract identifiers from end handling code
        }
        
        if (stmtText.contains("INVALID KEY") || stmtText.contains("NOT INVALID KEY")) {
            // Extract identifiers from key handling code
        }
        
        if (stmtText.contains("ON OVERFLOW") || stmtText.contains("NOT ON OVERFLOW")) {
            // Extract identifiers from overflow handling code
        }
    }

    /**
     * Method to collect file names and treat them as data items for dependency analysis
     * File names are important for understanding program dependencies
     */
    private static void collectFileReferences(CobolParser.StatementContext stmtCtx, Set<String> referencedDataItems) {
        // File operations reference file names which are important for dependency analysis
        if (stmtCtx.openStatement() != null || 
            stmtCtx.closeStatement() != null ||
            stmtCtx.readStatement() != null ||
            stmtCtx.writeStatement() != null ||
            stmtCtx.rewriteStatement() != null ||
            stmtCtx.deleteStatement() != null ||
            stmtCtx.startStatement() != null) {
            
            // File names are already collected in the individual statement handlers above
            // This method could be used for additional file-related processing
        }
    }

    /**
     * Method to collect procedure names referenced in statements
     * This helps with call graph analysis
     */
    private static void collectProcedureReferences(CobolParser.StatementContext stmtCtx, Set<String> referencedDataItems) {
        if (stmtCtx.performStatement() != null) {
            CobolParser.PerformStatementContext perfCtx = stmtCtx.performStatement();
            if (perfCtx.performProcedureStatement() != null) {
                for (CobolParser.ProcedureNameContext procCtx : perfCtx.performProcedureStatement().procedureName()) {
                    // Procedure names could be collected separately or included in referencedDataItems
                    // depending on your analysis needs
                    referencedDataItems.add("PROC:" + procCtx.getText());
                }
            }
        }
        
        if (stmtCtx.goToStatement() != null) {
            CobolParser.GoToStatementContext gotoCtx = stmtCtx.goToStatement();
            if (gotoCtx.goToStatementSimple() != null && 
                gotoCtx.goToStatementSimple().procedureName() != null) {
                referencedDataItems.add("PROC:" + gotoCtx.goToStatementSimple().procedureName().getText());
            }
            if (gotoCtx.goToDependingOnStatement() != null) {
                for (CobolParser.ProcedureNameContext procCtx : gotoCtx.goToDependingOnStatement().procedureName()) {
                    referencedDataItems.add("PROC:" + procCtx.getText());
                }
                if (gotoCtx.goToDependingOnStatement().identifier() != null) {
                    referencedDataItems.add(gotoCtx.goToDependingOnStatement().identifier().getText());
                }
            }
        }
    }

    /**
     * Enhanced main collection method that ensures comprehensive coverage
     */
    public static void collectAllReferencedDataItems(CobolParser.SentenceContext ctx, Set<String> referencedDataItems) {
        for (CobolParser.StatementContext stmtCtx : ctx.statement()) {
            // Main statement processing
            collectFromStatement(stmtCtx, referencedDataItems);
            
            // Additional processing for completeness
            collectFromExceptionClauses(stmtCtx, referencedDataItems);
            collectFileReferences(stmtCtx, referencedDataItems);
            collectProcedureReferences(stmtCtx, referencedDataItems);
        }
    }

    /**
     * Utility method to clean and normalize data item names
     * This helps with consistency in analysis
     */
    private static String normalizeDataItemName(String name) {
        if (name == null) return null;
        
        // Remove quotes if present
        String normalized = name.replaceAll("[\"\']", "");
        
        // Convert to uppercase for consistency
        normalized = normalized.toUpperCase();
        
        // Remove any leading/trailing whitespace
        normalized = normalized.trim();
        
        return normalized;
    }

    /**
     * Method to filter out system-generated or less relevant data items
     * This helps focus analysis on user-defined data items
     */
    private static boolean shouldIncludeDataItem(String dataItemName) {
        if (dataItemName == null || dataItemName.trim().isEmpty()) {
            return false;
        }
        
        String normalized = normalizeDataItemName(dataItemName);
        
        // Filter out literals and constants
        if (normalized.matches("^[0-9]+$") || // Pure numbers
            normalized.matches("^[0-9]*\\.[0-9]+$") || // Decimals
            normalized.startsWith("\"") || // String literals
            normalized.startsWith("'") || // String literals
            normalized.equals("ZERO") ||
            normalized.equals("ZEROS") ||
            normalized.equals("ZEROES") ||
            normalized.equals("SPACE") ||
            normalized.equals("SPACES") ||
            normalized.equals("HIGH-VALUE") ||
            normalized.equals("HIGH-VALUES") ||
            normalized.equals("LOW-VALUE") ||
            normalized.equals("LOW-VALUES") ||
            normalized.equals("NULL") ||
            normalized.equals("NULLS")) {
            return false;
        }
        
        // Include everything else
        return true;
    }
}

